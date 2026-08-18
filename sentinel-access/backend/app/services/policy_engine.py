import json
import re
from hashlib import sha256

from app.schemas.entities import (
    IdentityBaseline,
    PolicyEvaluation,
    PolicyRule,
    PolicyRuleResult,
    PolicySnapshot,
    SecurityEvent,
)
from app.services.baseline import event_frequency, parse_utc


CONTEXT_KEYS = {
    "new_source_or_location",
    "unusual_time",
    "new_service_or_action",
    "high_frequency",
}

# Splits camelCase/PascalCase and ACRONYMBoundary transitions into words so
# cloud provider action names (e.g. "AttachAdminPolicy", "IAMFullAccess")
# match the same space-separated phrases as snake_case/kebab-case actions.
_CAMEL_BOUNDARY = re.compile(r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])")


def _contains(action: str, phrases: tuple[str, ...]) -> bool:
    spaced = _CAMEL_BOUNDARY.sub(" ", action)
    normalized = spaced.lower().replace("_", " ").replace("-", " ")
    return any(phrase in normalized for phrase in phrases)


def _action_matches(condition_key: str, action: str) -> bool:
    if condition_key == "disable_or_remove_protection":
        return _contains(action, (
            "disable logging", "stop logging", "delete trail", "delete security policy",
            "remove protection", "disable audit", "turn off logging", "delete guardrail",
        ))
    if condition_key == "secret_or_credential_access":
        return _contains(action, (
            "secret", "credential", "vault", "protected key", "decrypt key", "get secret",
        ))
    if condition_key == "permission_or_admin_change":
        return _contains(action, (
            "permission", "administrator", "admin policy", "attach policy", "role change",
            "grant role", "grant privilege", "assign role", "set iam policy", "add member",
        ))
    if condition_key == "login_or_key_change":
        return _contains(action, (
            "access key", "login change", "password", "mfa", "sign in setting", "credential reset",
        ))
    if condition_key == "read_only":
        return _contains(action, ("read", "get", "list", "describe", "view", "enumerate", "download"))
    return False


def _hour_in_baseline(event: SecurityEvent, baseline: IdentityBaseline) -> bool:
    if not baseline.usualHours:
        return False
    event_minutes = parse_utc(event.timestampUtc).hour * 60 + parse_utc(event.timestampUtc).minute
    for span in baseline.usualHours:
        start_hour, start_minute = (int(value) for value in span.start.split(":"))
        end_hour, end_minute = (int(value) for value in span.end.split(":"))
        if start_hour * 60 + start_minute <= event_minutes <= end_hour * 60 + end_minute:
            return True
    return False


def _base_condition(
    rule: PolicyRule,
    event: SecurityEvent,
    baseline: IdentityBaseline,
    sequence: list[SecurityEvent],
    facts: dict[str, bool | None],
) -> tuple[str, str, list[str]]:
    key = rule.conditionKey
    baseline_known = baseline.confidence == "high"
    if key in CONTEXT_KEYS and not baseline_known:
        return "unknown", "The 30-day baseline has insufficient history for this condition.", []

    if key == "new_source_or_location":
        source_new = bool(event.sourceIp) and event.sourceIp not in baseline.usualSourceIps
        location_new = bool(event.location) and event.location not in baseline.usualLocations
        matched = source_new or location_new
        evidence = "Source or location was absent from the established baseline." if matched else "Source and location match the established baseline."
        facts["new_source_or_location"] = matched
        return ("matched" if matched else "not_matched"), evidence, [event.eventId]
    if key == "unusual_time":
        matched = not _hour_in_baseline(event, baseline)
        facts["unusual_time"] = matched
        evidence = "Event occurred outside the identity's usual activity hours." if matched else "Event occurred within usual activity hours."
        return ("matched" if matched else "not_matched"), evidence, [event.eventId]
    if key == "new_service_or_action":
        matched = event.cloudService not in baseline.usualServices or event.action not in baseline.usualActions
        facts["new_service_or_action"] = matched
        evidence = "Service or action was absent from the established baseline." if matched else "Service and action match the established baseline."
        return ("matched" if matched else "not_matched"), evidence, [event.eventId]
    if key == "high_frequency":
        observed = event_frequency(event, sequence)
        matched = observed > baseline.frequencyP95
        facts["high_frequency"] = matched
        evidence = f"Observed {observed} events in 15 minutes versus historical p95 {baseline.frequencyP95:g}."
        return ("matched" if matched else "not_matched"), evidence, [event.eventId]

    if rule.category == "action":
        matched = _action_matches(key, event.action)
        facts[key] = matched
        evidence = f"Action classification {'matched' if matched else 'did not match'} {key}."
        return ("matched" if matched else "not_matched"), evidence, [event.eventId]

    if key == "new_location_admin_change":
        if not baseline_known:
            return "unknown", "New-location evidence is unknown because baseline history is insufficient.", []
        matched = bool(facts.get("new_source_or_location")) and bool(facts.get("permission_or_admin_change"))
        return ("matched" if matched else "not_matched"), "New source/location and administrator permission change occurred together.", [event.eventId]
    if key == "unusual_time_secret_access":
        if not baseline_known:
            return "unknown", "Unusual-time evidence is unknown because baseline history is insufficient.", []
        matched = bool(facts.get("unusual_time")) and bool(facts.get("secret_or_credential_access"))
        return ("matched" if matched else "not_matched"), "Unusual time and secret access occurred together.", [event.eventId]
    if key == "new_service_high_frequency":
        if not baseline_known:
            return "unknown", "Service/frequency evidence is unknown because baseline history is insufficient.", []
        matched = bool(facts.get("new_service_or_action")) and bool(facts.get("high_frequency"))
        return ("matched" if matched else "not_matched"), "New service/action and high event frequency occurred together.", [event.eventId]
    if key == "protection_after_privilege":
        prior = [
            item for item in sequence
            if item.eventId != event.eventId and _action_matches("permission_or_admin_change", item.action)
        ]
        matched = _action_matches("disable_or_remove_protection", event.action) and bool(prior)
        ids = [prior[-1].eventId, event.eventId] if prior else [event.eventId]
        return ("matched" if matched else "not_matched"), "A protection change followed a privilege change in the bounded sequence.", ids

    raise ValueError(f"Unsupported policy condition key: {key}")


def evaluate_policies(
    event: SecurityEvent,
    baseline: IdentityBaseline,
    sequence: list[SecurityEvent],
    policies: list[PolicyRule],
) -> tuple[PolicySnapshot, PolicyEvaluation]:
    snapshot_payload = {
        "policyVersion": policies[0].policyVersion if policies else "policy-catalog-v1",
        "rules": [policy.model_dump() for policy in policies],
    }
    snapshot_json = json.dumps(snapshot_payload, sort_keys=True, separators=(",", ":"))
    snapshot_hash = sha256(snapshot_json.encode()).hexdigest()
    snapshot = PolicySnapshot(
        policyVersion=snapshot_payload["policyVersion"],
        snapshotHash=snapshot_hash,
        rules=policies,
    )

    preliminary: list[PolicyRuleResult] = []
    facts: dict[str, bool | None] = {}
    for rule in policies:
        if not rule.enabled:
            preliminary.append(PolicyRuleResult(
                ruleId=rule.ruleId,
                category=rule.category,
                state="disabled",
                selected=False,
                configuredPoints=rule.points,
                awardedPoints=0,
                severityFloor=rule.severityFloor,
                evidence="Rule was disabled in this policy snapshot.",
                evidenceEventIds=[],
            ))
            continue
        state, evidence, evidence_ids = _base_condition(rule, event, baseline, sequence, facts)
        preliminary.append(PolicyRuleResult(
            ruleId=rule.ruleId,
            category=rule.category,
            state=state,
            selected=False,
            configuredPoints=rule.points,
            awardedPoints=0,
            severityFloor=rule.severityFloor,
            evidence=evidence,
            evidenceEventIds=evidence_ids if state == "matched" else [],
        ))

    selected_ids: set[str] = {
        result.ruleId for result in preliminary if result.category == "context" and result.state == "matched"
    }
    for category in ("action", "compound_sequence"):
        matches = [result for result in preliminary if result.category == category and result.state == "matched"]
        if matches:
            selected_ids.add(max(matches, key=lambda result: result.configuredPoints).ruleId)

    results: list[PolicyRuleResult] = []
    for result in preliminary:
        selected = result.ruleId in selected_ids
        results.append(result.model_copy(update={
            "selected": selected,
            "awardedPoints": result.configuredPoints if selected else 0,
        }))

    score = min(100, sum(result.awardedPoints for result in results))
    matched_floors = [
        result.severityFloor for result in results
        if result.state == "matched" and result.severityFloor is not None
    ]
    floor = "Critical" if "Critical" in matched_floors else "High" if "High" in matched_floors else None
    floor_minimum = 85 if floor == "Critical" else 65 if floor == "High" else 0
    evaluation_id = f"pe-{sha256(f'{event.eventId}|{baseline.baselineId}|{snapshot_hash}'.encode()).hexdigest()[:24]}"
    evaluation = PolicyEvaluation(
        policyEvaluationId=evaluation_id,
        policyVersion=snapshot.policyVersion,
        policyScore=score,
        severityFloor=floor,
        severityFloorMinimum=floor_minimum,
        ruleResults=results,
        snapshotHash=snapshot_hash,
    )
    return snapshot, evaluation

