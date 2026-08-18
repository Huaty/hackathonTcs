from app.schemas.entities import BaselineHours, IdentityBaseline, PolicyRule, SecurityEvent
from app.services.policy_engine import evaluate_policies

POLICY_VERSION = "policy-catalog-v1"

# Full Policy Catalog v1, mirroring specs/004-contextual-risk-scoring/spec.md.
CATALOG = [
    PolicyRule(
        ruleId="POL-NEW-SOURCE", title="New source or location", description="", enabled=True,
        category="context", conditionKey="new_source_or_location", points=20, severityFloor=None,
        policyVersion=POLICY_VERSION,
    ),
    PolicyRule(
        ruleId="POL-UNUSUAL-TIME", title="Unusual activity time", description="", enabled=True,
        category="context", conditionKey="unusual_time", points=10, severityFloor=None,
        policyVersion=POLICY_VERSION,
    ),
    PolicyRule(
        ruleId="POL-NEW-SERVICE-ACTION", title="New service or action", description="", enabled=True,
        category="context", conditionKey="new_service_or_action", points=15, severityFloor=None,
        policyVersion=POLICY_VERSION,
    ),
    PolicyRule(
        ruleId="POL-HIGH-FREQUENCY", title="High-frequency activity", description="", enabled=True,
        category="context", conditionKey="high_frequency", points=15, severityFloor=None,
        policyVersion=POLICY_VERSION,
    ),
    PolicyRule(
        ruleId="POL-READ-ONLY", title="Normal read-only action", description="", enabled=True,
        category="action", conditionKey="read_only", points=0, severityFloor=None,
        policyVersion=POLICY_VERSION,
    ),
    PolicyRule(
        ruleId="POL-LOGIN-KEY-CHANGE", title="Login or access-key change", description="", enabled=True,
        category="action", conditionKey="login_or_key_change", points=20, severityFloor=None,
        policyVersion=POLICY_VERSION,
    ),
    PolicyRule(
        ruleId="POL-PERMISSION-CHANGE", title="Permission or admin change", description="", enabled=True,
        category="action", conditionKey="permission_or_admin_change", points=35, severityFloor=None,
        policyVersion=POLICY_VERSION,
    ),
    PolicyRule(
        ruleId="POL-SECRET-ACCESS", title="Secret or credential access", description="", enabled=True,
        category="action", conditionKey="secret_or_credential_access", points=40, severityFloor=None,
        policyVersion=POLICY_VERSION,
    ),
    PolicyRule(
        ruleId="POL-DISABLE-PROTECTION", title="Disable security protection", description="", enabled=True,
        category="action", conditionKey="disable_or_remove_protection", points=70, severityFloor="High",
        policyVersion=POLICY_VERSION,
    ),
    PolicyRule(
        ruleId="POL-NEW-LOCATION-ADMIN", title="New location plus admin change", description="", enabled=True,
        category="compound_sequence", conditionKey="new_location_admin_change", points=20,
        severityFloor="High", policyVersion=POLICY_VERSION,
    ),
    PolicyRule(
        ruleId="POL-UNUSUAL-TIME-SECRET", title="Unusual time plus secret access", description="",
        enabled=True, category="compound_sequence", conditionKey="unusual_time_secret_access", points=15,
        severityFloor=None, policyVersion=POLICY_VERSION,
    ),
    PolicyRule(
        ruleId="POL-NEW-SERVICE-BURST", title="New service plus high frequency", description="", enabled=True,
        category="compound_sequence", conditionKey="new_service_high_frequency", points=10,
        severityFloor=None, policyVersion=POLICY_VERSION,
    ),
    PolicyRule(
        ruleId="POL-PROTECTION-AFTER-PRIVILEGE", title="Protection removed after privilege change",
        description="", enabled=True, category="compound_sequence",
        conditionKey="protection_after_privilege", points=30, severityFloor="Critical",
        policyVersion=POLICY_VERSION,
    ),
]

RULES_BY_ID = {rule.ruleId: rule for rule in CATALOG}


def rule(rule_id: str, **overrides) -> PolicyRule:
    return RULES_BY_ID[rule_id].model_copy(update=overrides)


def high_confidence_baseline(**overrides) -> IdentityBaseline:
    fields = dict(
        baselineId="base-test",
        identityId="id-test",
        windowStartUtc="2026-07-02T00:00:00Z",
        windowEndUtc="2026-08-01T00:00:00Z",
        usualHours=[BaselineHours(start="09:00", end="17:59")],
        usualSourceIps=["10.0.0.5"],
        usualLocations=["US"],
        usualServices=["s3"],
        usualActions=["GetObject"],
        frequencyP95=3.0,
        sampleCount=24,
        activeDayCount=8,
        confidence="high",
        unknownFields=[],
        baselineVersion="identity-baseline-v1",
        createdAt="2026-08-01T00:00:00Z",
    )
    fields.update(overrides)
    return IdentityBaseline(**fields)


def low_confidence_baseline(**overrides) -> IdentityBaseline:
    fields = dict(
        baselineId="base-test-low",
        identityId="id-test",
        windowStartUtc="2026-07-02T00:00:00Z",
        windowEndUtc="2026-08-01T00:00:00Z",
        usualHours=[],
        usualSourceIps=[],
        usualLocations=[],
        usualServices=[],
        usualActions=[],
        frequencyP95=0,
        sampleCount=2,
        activeDayCount=1,
        confidence="low",
        unknownFields=["source", "location", "hours", "services", "actions", "frequency"],
        baselineVersion="identity-baseline-v1",
        createdAt="2026-08-01T00:00:00Z",
    )
    fields.update(overrides)
    return IdentityBaseline(**fields)


def event(**overrides) -> SecurityEvent:
    fields = dict(
        eventId="EVT-1",
        identityId="id-test",
        timestampUtc="2026-08-01T09:05:00Z",
        sourceIp="10.0.0.5",
        location="US",
        cloudService="s3",
        action="GetObject",
        resource="bucket/x",
        outcome="success",
    )
    fields.update(overrides)
    return SecurityEvent(**fields)


def result_for(evaluation, rule_id: str):
    return next(r for r in evaluation.ruleResults if r.ruleId == rule_id)


# -- Context conditions (all additive) --------------------------------------


def test_new_source_or_location_matches_new_ip():
    e = event(sourceIp="203.0.113.9")
    _, evaluation = evaluate_policies(e, high_confidence_baseline(), [e], CATALOG)
    r = result_for(evaluation, "POL-NEW-SOURCE")
    assert r.state == "matched"
    assert r.selected is True
    assert r.awardedPoints == 20


def test_new_source_or_location_not_matched_within_baseline():
    e = event()
    _, evaluation = evaluate_policies(e, high_confidence_baseline(), [e], CATALOG)
    r = result_for(evaluation, "POL-NEW-SOURCE")
    assert r.state == "not_matched"
    assert r.awardedPoints == 0


def test_unusual_time_matches_outside_baseline_hours():
    e = event(timestampUtc="2026-08-01T02:00:00Z")
    _, evaluation = evaluate_policies(e, high_confidence_baseline(), [e], CATALOG)
    r = result_for(evaluation, "POL-UNUSUAL-TIME")
    assert r.state == "matched"
    assert r.awardedPoints == 10


def test_unusual_time_not_matched_within_baseline_hours():
    e = event(timestampUtc="2026-08-01T10:00:00Z")
    _, evaluation = evaluate_policies(e, high_confidence_baseline(), [e], CATALOG)
    r = result_for(evaluation, "POL-UNUSUAL-TIME")
    assert r.state == "not_matched"


def test_new_service_or_action_matches_new_service():
    e = event(cloudService="iam")
    _, evaluation = evaluate_policies(e, high_confidence_baseline(), [e], CATALOG)
    r = result_for(evaluation, "POL-NEW-SERVICE-ACTION")
    assert r.state == "matched"
    assert r.awardedPoints == 15


def test_new_service_or_action_not_matched():
    e = event()
    _, evaluation = evaluate_policies(e, high_confidence_baseline(), [e], CATALOG)
    r = result_for(evaluation, "POL-NEW-SERVICE-ACTION")
    assert r.state == "not_matched"


def test_high_frequency_matches_when_over_p95():
    e = event()
    prior = [event(eventId=f"EVT-P{i}", timestampUtc=f"2026-08-01T09:0{i}:00Z") for i in range(4)]
    _, evaluation = evaluate_policies(e, high_confidence_baseline(frequencyP95=3.0), prior + [e], CATALOG)
    r = result_for(evaluation, "POL-HIGH-FREQUENCY")
    assert r.state == "matched"
    assert r.awardedPoints == 15


def test_high_frequency_not_matched_when_under_p95():
    e = event()
    _, evaluation = evaluate_policies(e, high_confidence_baseline(frequencyP95=10.0), [e], CATALOG)
    r = result_for(evaluation, "POL-HIGH-FREQUENCY")
    assert r.state == "not_matched"


def test_all_context_rules_are_additive():
    e = event(
        sourceIp="203.0.113.9",
        timestampUtc="2026-08-01T02:00:00Z",
        cloudService="iam",
        action="GetRole",
    )
    prior = [event(eventId=f"EVT-P{i}", timestampUtc=f"2026-08-01T01:5{i}:00Z", cloudService="iam") for i in range(4)]
    _, evaluation = evaluate_policies(e, high_confidence_baseline(frequencyP95=3.0), prior + [e], CATALOG)
    context_points = sum(r.awardedPoints for r in evaluation.ruleResults if r.category == "context")
    assert context_points == 20 + 10 + 15 + 15  # all four context rules matched and additive
    for rule_id in ("POL-NEW-SOURCE", "POL-UNUSUAL-TIME", "POL-NEW-SERVICE-ACTION", "POL-HIGH-FREQUENCY"):
        assert result_for(evaluation, rule_id).state == "matched"


# -- Action conditions (highest matching only) -------------------------------


def test_read_only_action_awards_zero():
    e = event(action="ListBuckets")
    _, evaluation = evaluate_policies(e, high_confidence_baseline(usualActions=["ListBuckets"]), [e], CATALOG)
    r = result_for(evaluation, "POL-READ-ONLY")
    assert r.state == "matched"
    assert r.selected is True
    assert r.awardedPoints == 0


def test_only_highest_matching_action_rule_is_selected():
    action = "Reset Password And Attach Admin Policy"
    e = event(action=action)
    # Isolate action-selection behavior: keep the action itself within the
    # baseline so POL-NEW-SERVICE-ACTION doesn't also contribute points.
    _, evaluation = evaluate_policies(e, high_confidence_baseline(usualActions=[action]), [e], CATALOG)
    login = result_for(evaluation, "POL-LOGIN-KEY-CHANGE")
    permission = result_for(evaluation, "POL-PERMISSION-CHANGE")
    assert login.state == "matched"
    assert permission.state == "matched"
    assert permission.selected is True
    assert permission.awardedPoints == 35
    # matched-but-unselected rule remains visible with zero awarded points
    assert login.selected is False
    assert login.awardedPoints == 0
    assert evaluation.policyScore == 35


def test_camelcase_cloud_action_names_match_action_phrases():
    e = event(action="AttachAdminPolicy")
    _, evaluation = evaluate_policies(e, high_confidence_baseline(), [e], CATALOG)
    r = result_for(evaluation, "POL-PERMISSION-CHANGE")
    assert r.state == "matched"
    assert r.awardedPoints == 35


# -- Compound/sequence conditions (highest matching only) --------------------


def test_new_location_admin_change_matches_and_carries_high_floor():
    e = event(sourceIp="203.0.113.9", location="DE", action="Grant Administrator Role")
    _, evaluation = evaluate_policies(e, high_confidence_baseline(), [e], CATALOG)
    r = result_for(evaluation, "POL-NEW-LOCATION-ADMIN")
    assert r.state == "matched"
    assert r.selected is True
    assert r.severityFloor == "High"
    assert evaluation.severityFloor == "High"
    assert evaluation.severityFloorMinimum == 65


def test_unusual_time_secret_access_matches():
    e = event(timestampUtc="2026-08-01T02:00:00Z", action="GetSecretValue")
    _, evaluation = evaluate_policies(e, high_confidence_baseline(), [e], CATALOG)
    r = result_for(evaluation, "POL-UNUSUAL-TIME-SECRET")
    assert r.state == "matched"


def test_new_service_high_frequency_matches():
    e = event(cloudService="iam")
    prior = [event(eventId=f"EVT-P{i}", timestampUtc=f"2026-08-01T09:0{i}:00Z", cloudService="iam") for i in range(4)]
    _, evaluation = evaluate_policies(e, high_confidence_baseline(frequencyP95=3.0), prior + [e], CATALOG)
    r = result_for(evaluation, "POL-NEW-SERVICE-BURST")
    assert r.state == "matched"


def test_protection_after_privilege_requires_prior_privilege_change_in_sequence():
    privilege_event = event(eventId="EVT-PRIV", timestampUtc="2026-08-01T09:00:00Z", action="Grant Administrator Role")
    protection_event = event(eventId="EVT-PROT", timestampUtc="2026-08-01T09:10:00Z", action="Disable Logging Trail")
    _, evaluation = evaluate_policies(
        protection_event, high_confidence_baseline(), [privilege_event, protection_event], CATALOG
    )
    r = result_for(evaluation, "POL-PROTECTION-AFTER-PRIVILEGE")
    assert r.state == "matched"
    assert set(r.evidenceEventIds) == {"EVT-PRIV", "EVT-PROT"}


def test_protection_after_privilege_not_matched_without_prior_privilege_change():
    protection_event = event(eventId="EVT-PROT", timestampUtc="2026-08-01T09:10:00Z", action="Disable Logging Trail")
    _, evaluation = evaluate_policies(protection_event, high_confidence_baseline(), [protection_event], CATALOG)
    r = result_for(evaluation, "POL-PROTECTION-AFTER-PRIVILEGE")
    assert r.state == "not_matched"


def test_only_highest_matching_compound_rule_is_selected():
    e = event(
        sourceIp="203.0.113.9",
        location="DE",
        timestampUtc="2026-08-01T02:00:00Z",
        action="Attach Admin Policy And Access Secret Vault",
    )
    _, evaluation = evaluate_policies(e, high_confidence_baseline(), [e], CATALOG)
    location_admin = result_for(evaluation, "POL-NEW-LOCATION-ADMIN")
    time_secret = result_for(evaluation, "POL-UNUSUAL-TIME-SECRET")
    assert location_admin.state == "matched"
    assert time_secret.state == "matched"
    assert location_admin.selected is True  # 20 points beats 15
    assert time_secret.selected is False
    assert time_secret.awardedPoints == 0


def test_strongest_floor_prefers_critical_over_high():
    privilege_event = event(eventId="EVT-PRIV", timestampUtc="2026-08-01T09:00:00Z", action="Grant Administrator Role")
    protection_event = event(eventId="EVT-PROT", timestampUtc="2026-08-01T09:10:00Z", action="Disable Logging Trail")
    _, evaluation = evaluate_policies(
        protection_event, high_confidence_baseline(), [privilege_event, protection_event], CATALOG
    )
    # POL-DISABLE-PROTECTION (High) and POL-PROTECTION-AFTER-PRIVILEGE (Critical) both match.
    assert result_for(evaluation, "POL-DISABLE-PROTECTION").state == "matched"
    assert result_for(evaluation, "POL-PROTECTION-AFTER-PRIVILEGE").state == "matched"
    assert evaluation.severityFloor == "Critical"
    assert evaluation.severityFloorMinimum == 85


# -- Disabled rules ------------------------------------------------------


def test_disabled_rule_reports_disabled_and_awards_zero():
    catalog = [rule("POL-NEW-SOURCE", enabled=False)] + [r for r in CATALOG if r.ruleId != "POL-NEW-SOURCE"]
    e = event(sourceIp="203.0.113.9")
    _, evaluation = evaluate_policies(e, high_confidence_baseline(), [e], catalog)
    r = result_for(evaluation, "POL-NEW-SOURCE")
    assert r.state == "disabled"
    assert r.selected is False
    assert r.awardedPoints == 0


# -- Unknown baseline ------------------------------------------------------


def test_context_rules_report_unknown_when_baseline_low_confidence():
    e = event(sourceIp="203.0.113.9")
    _, evaluation = evaluate_policies(e, low_confidence_baseline(), [e], CATALOG)
    for rule_id in ("POL-NEW-SOURCE", "POL-UNUSUAL-TIME", "POL-NEW-SERVICE-ACTION", "POL-HIGH-FREQUENCY"):
        r = result_for(evaluation, rule_id)
        assert r.state == "unknown"
        assert r.awardedPoints == 0
    assert evaluation.policyScore == 0


def test_compound_rules_report_unknown_when_baseline_low_confidence():
    e = event(sourceIp="203.0.113.9", location="DE", action="Grant Administrator Role")
    _, evaluation = evaluate_policies(e, low_confidence_baseline(), [e], CATALOG)
    r = result_for(evaluation, "POL-NEW-LOCATION-ADMIN")
    assert r.state == "unknown"
    assert r.severityFloor is None or evaluation.severityFloor is None


# -- Cap at 100 ------------------------------------------------------------


def test_policy_score_capped_at_100():
    e = event(
        sourceIp="203.0.113.9",
        location="DE",
        timestampUtc="2026-08-01T02:00:00Z",
        cloudService="iam",
        action="Disable Logging Trail",
    )
    prior = [event(eventId=f"EVT-P{i}", timestampUtc=f"2026-08-01T01:5{i}:00Z", cloudService="iam") for i in range(4)]
    _, evaluation = evaluate_policies(e, high_confidence_baseline(frequencyP95=3.0), prior + [e], CATALOG)
    # context 20+10+15+15=60, action disable-protection=70 -> raw 130, capped at 100
    assert evaluation.policyScore == 100
