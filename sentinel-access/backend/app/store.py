import json
import random
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from itertools import count
from uuid import uuid4

from app import db
from app.schemas.entities import (
    AccessTrendPoint,
    ActivityEvent,
    AIContextDecision,
    BaselineHours,
    CloudSource,
    Configuration,
    DatasetImportResult,
    Finding,
    Identity,
    IdentityBaseline,
    IdentityDetail,
    IdentityProfileResponse,
    IdentityRiskSummary,
    ModelRationale,
    MostUrgentCase,
    PolicyRule,
    RationaleSignal,
    ReportTemplate,
    RiskAssessment,
    RiskBaselineRef,
    SecurityEvent,
    ServiceRisk,
    ServiceRiskSummary,
    SummaryMetrics,
)
from app.seed_data import seed_database
from app.services import PROMPT_VERSION, SCORING_VERSION
from app.services.ai_risk_context import request_ai_decision
from app.services.baseline import build_baseline, parse_utc
from app.services.identity_resolution import initials_for, resolve_identity_id
from app.services.policy_engine import evaluate_policies
from app.services.risk_scoring import calculate_risk

_finding_id_counter = count(1)

SEQUENCE_WINDOW_MINUTES = 60
SEQUENCE_MAX_EVENTS = 20

# Fictitious, demo-safe "something interesting just happened" scenarios used
# by simulate_event_for_identity — reserved/documentation IP ranges only,
# no real hosts or credentials.
SIMULATED_EVENT_SCENARIOS = [
    {
        "sourceIp": "203.0.113.77", "location": "DE", "cloudService": "iam",
        "action": "AttachAdminPolicy", "resource": "role/prod-admin",
    },
    {
        "sourceIp": "198.51.100.23", "location": "BR", "cloudService": "secretsmanager",
        "action": "GetSecretValue", "resource": "prod/db-password",
    },
    {
        "sourceIp": "192.0.2.44", "location": "SG", "cloudService": "cloudtrail",
        "action": "StopLogging", "resource": "trail/prod",
    },
    {
        "sourceIp": "203.0.113.201", "location": "AU", "cloudService": "iam",
        "action": "CreateAccessKey", "resource": "user/service-bot",
    },
]


class EventNotFoundError(Exception):
    """Raised when a risk assessment is requested for an eventId that has no stored SecurityEvent."""


class RiskAssessmentPrerequisiteError(Exception):
    """Raised when a stable identity or another scoring prerequisite cannot be resolved for an event."""


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _finding_from_row(row) -> Finding:
    return Finding(
        id=row["id"],
        severity=row["severity"],
        title=row["title"],
        entity=row["entity"],
        role=row["role"],
        source=row["source"],
        region=row["region"],
        service=row["service"],
        score=row["score"],
        time=row["time"],
        description=row["description"],
        signals=json.loads(row["signals"]),
        baseline=row["baseline"],
        recommended=row["recommended"],
        status=row["status"],
    )


def _activity_event_from_row(row) -> ActivityEvent:
    return ActivityEvent(
        time=row["time"],
        actor=row["actor"],
        action=row["action"],
        source=row["source"],
        system=row["system"],
        status=row["status"],
        tone=row["tone"],
    )


def _identity_from_row(row) -> Identity:
    return Identity(
        identityId=row["identity_id"],
        name=row["name"],
        initials=row["initials"],
        role=row["role"],
        activity=row["activity"],
        score=row["score"],
        color=row["color"],
        description=row["description"],
        identityType=row["identity_type"],
        status=row["status"],
        homeTimezone=row["home_timezone"],
        lastSeenAt=row["last_seen_at"],
    )


def _cloud_source_from_row(row) -> CloudSource:
    return CloudSource(
        name=row["name"],
        type=row["type"],
        status=row["status"],
        eventsToday=row["eventsToday"],
        health=row["health"],
        icon=row["icon"],
        color=row["color"],
        dataFreshnessMin=row["dataFreshnessMin"],
    )


def _policy_from_row(row) -> PolicyRule:
    return PolicyRule(
        ruleId=row["rule_id"],
        title=row["title"],
        description=row["description"],
        enabled=bool(row["enabled"]),
        category=row["category"],
        conditionKey=row["condition_key"],
        points=row["points"],
        severityFloor=row["severity_floor"],
        policyVersion=row["policy_version"],
    )


def _report_from_row(row) -> ReportTemplate:
    return ReportTemplate(title=row["title"], detail=row["detail"], period=row["period"], type=row["type"])


def _security_event_from_row(row) -> SecurityEvent:
    return SecurityEvent(
        eventId=row["event_id"],
        identityId=row["identity_id"],
        timestampUtc=row["timestamp_utc"],
        sourceIp=row["source_ip"],
        location=row["location"],
        cloudService=row["cloud_service"],
        action=row["action"],
        resource=row["resource"],
        outcome=row["outcome"],
        sessionId=row["session_id"],
        correlationId=row["correlation_id"],
        rawPayload=json.loads(row["raw_payload"]),
    )


def _identity_baseline_from_row(row) -> IdentityBaseline:
    return IdentityBaseline(
        baselineId=row["baseline_id"],
        identityId=row["identity_id"],
        windowStartUtc=row["window_start_utc"],
        windowEndUtc=row["window_end_utc"],
        usualHours=[BaselineHours(**h) for h in json.loads(row["usual_hours"])],
        usualSourceIps=json.loads(row["usual_source_ips"]),
        usualLocations=json.loads(row["usual_locations"]),
        usualServices=json.loads(row["usual_services"]),
        usualActions=json.loads(row["usual_actions"]),
        frequencyP95=row["frequency_p95"],
        sampleCount=row["sample_count"],
        activeDayCount=row["active_day_count"],
        confidence=row["confidence"],
        unknownFields=json.loads(row["unknown_fields"]),
        baselineVersion=row["baseline_version"],
        createdAt=row["created_at"],
    )


def _ai_decision_from_row(row) -> AIContextDecision:
    return AIContextDecision(
        aiDecisionId=row["ai_decision_id"],
        status=row["status"],
        adjustmentRequested=row["adjustment_requested"],
        adjustmentApplied=row["adjustment_applied"],
        confidence=row["confidence"],
        riskFactors=json.loads(row["risk_factors"]),
        mitigatingFactors=json.loads(row["mitigating_factors"]),
        evidenceEventIds=json.loads(row["evidence_event_ids"]),
        explanation=row["explanation"],
        validationErrors=json.loads(row["validation_errors"]),
        model=row["model"],
        promptVersion=row["prompt_version"],
    )


def _meta(key: str) -> str:
    row = db.query_one("SELECT value FROM meta WHERE key = ?", (key,))
    return row["value"] if row is not None else ""


class Store:
    # -- Findings -----------------------------------------------------

    def get_findings(self) -> list[Finding]:
        rows = db.query("SELECT * FROM findings ORDER BY rowid ASC")
        return [_finding_from_row(r) for r in rows]

    def get_finding(self, finding_id: str) -> Finding | None:
        row = db.query_one("SELECT * FROM findings WHERE id = ?", (finding_id,))
        return _finding_from_row(row) if row is not None else None

    def update_finding_status(self, finding_id: str, status: str) -> Finding | None:
        if self.get_finding(finding_id) is None:
            return None
        db.execute("UPDATE findings SET status = ? WHERE id = ?", (status, finding_id))
        return self.get_finding(finding_id)

    def add_finding(self, finding: Finding) -> Finding:
        floor_row = db.query_one("SELECT MIN(rowid) AS floor FROM findings")
        floor = floor_row["floor"]
        new_rowid = (floor if floor is not None else 1) - 1
        db.execute(
            "INSERT INTO findings (rowid, id, severity, title, entity, role, source, region, service, score, "
            "time, description, signals, baseline, recommended, status) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                new_rowid, finding.id, finding.severity, finding.title, finding.entity, finding.role,
                finding.source, finding.region, finding.service, finding.score, finding.time,
                finding.description, json.dumps(finding.signals), finding.baseline, finding.recommended,
                finding.status,
            ),
        )
        return finding

    def next_finding_id(self) -> str:
        return f"ALT-SIM-{next(_finding_id_counter):04d}"

    def get_finding_explanation(self, finding_id: str) -> str | None:
        row = db.query_one("SELECT explanation FROM finding_explanations WHERE finding_id = ?", (finding_id,))
        return row["explanation"] if row is not None else None

    def cache_finding_explanation(self, finding_id: str, explanation: str) -> None:
        db.execute(
            "INSERT INTO finding_explanations (finding_id, explanation) VALUES (?, ?) "
            "ON CONFLICT(finding_id) DO UPDATE SET explanation = excluded.explanation",
            (finding_id, explanation),
        )

    def compute_summary_metrics(self) -> SummaryMetrics:
        # needsAttention / mostUrgentCase are derived live from the current
        # findings list, not a static seed figure: a finding needs attention
        # until it has been escalated (handed off) — "open"/None and
        # "in_progress" both still count. activitiesChecked is likewise
        # derived live, from the current activity_log row count, so it
        # grows immediately as dataset uploads append rows (003-sqlite-storage).
        active = [f for f in self.get_findings() if f.status != "escalated"]
        if active:
            top = max(active, key=lambda f: f.score)
            most_urgent = MostUrgentCase(rank="01", label=top.title)
        else:
            most_urgent = MostUrgentCase(rank="-", label="No active findings")

        activities_checked = db.query_one("SELECT COUNT(*) AS n FROM activity_log")["n"]

        return SummaryMetrics(
            activitiesChecked=activities_checked,
            needsAttention=len(active),
            mostUrgentCase=most_urgent,
            averageReviewTime=_meta("average_review_time"),
            signalConfidencePct=float(_meta("signal_confidence_pct")),
            identityCoveragePct=int(_meta("identity_coverage_pct")),
        )

    # -- Activity log ---------------------------------------------------

    def get_activity_log(self) -> tuple[list[ActivityEvent], str]:
        rows = db.query("SELECT * FROM activity_log ORDER BY id ASC")
        source = _meta("activity_source") or "seed"
        return [_activity_event_from_row(r) for r in rows], source

    def append_activity_events(self, events: list[ActivityEvent]) -> int:
        db.executemany(
            "INSERT INTO activity_log (time, actor, action, source, system, status, tone) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            [(e.time, e.actor, e.action, e.source, e.system, e.status, e.tone) for e in events],
        )
        db.execute(
            "INSERT INTO meta (key, value) VALUES ('activity_source', 'imported') "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value"
        )
        return len(events)

    # -- Identities / estate ---------------------------------------------

    def get_identities(self) -> list[Identity]:
        rows = db.query("SELECT * FROM identities ORDER BY rowid ASC")
        return [_identity_from_row(r) for r in rows]

    def get_identity_by_id(self, identity_id: str) -> Identity | None:
        row = db.query_one("SELECT * FROM identities WHERE identity_id = ?", (identity_id,))
        return _identity_from_row(row) if row is not None else None

    def import_identities(self, records: list[dict]) -> DatasetImportResult:
        """Upserts identity directory records by stable identityId (FR-001,
        FR-020). Display-name/case changes for the same identityId update
        the existing row rather than creating a second identity."""
        created = 0
        updated = 0
        errors: list[str] = []
        for index, raw in enumerate(records, start=1):
            identity_id = resolve_identity_id(raw)
            if not identity_id:
                errors.append(f"Row {index}: could not resolve a stable identityId")
                continue
            name = str(raw.get("name") or raw.get("principalName") or identity_id)
            fields = (
                name,
                str(raw.get("initials") or initials_for(name)),
                str(raw.get("role", "Unknown")),
                str(raw.get("activity", "No recent activity")),
                int(raw.get("score", 0)),
                str(raw.get("color", "#39e0c5")),
                str(raw.get("description", "")),
                str(raw.get("identityType", "human")),
                str(raw.get("status", "active")),
                str(raw.get("homeTimezone", "UTC")),
                raw.get("lastSeenAt"),
            )
            existing = db.query_one("SELECT identity_id FROM identities WHERE identity_id = ?", (identity_id,))
            if existing is None:
                db.execute(
                    "INSERT INTO identities (identity_id, name, initials, role, activity, score, color, "
                    "description, identity_type, status, home_timezone, last_seen_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (identity_id,) + fields,
                )
                created += 1
            else:
                db.execute(
                    "UPDATE identities SET name = ?, initials = ?, role = ?, activity = ?, score = ?, "
                    "color = ?, description = ?, identity_type = ?, status = ?, home_timezone = ?, "
                    "last_seen_at = ? WHERE identity_id = ?",
                    fields + (identity_id,),
                )
                updated += 1
        return DatasetImportResult(
            acceptedCount=created + updated, rejectedCount=len(errors), errors=errors[:20],
            duplicateCount=0, identitiesCreated=created, identitiesUpdated=updated, eventsStored=0,
        )

    def import_events(self, records: list[dict]) -> DatasetImportResult:
        """Imports normalized security events. Unresolved identities are
        rejected rather than name-guessed (FR-022); duplicate eventIds are
        counted but never inserted twice; accepted rows commit atomically."""
        known_identity_ids = {identity.identityId for identity in self.get_identities()}
        existing_event_ids = {row["event_id"] for row in db.query("SELECT event_id FROM security_events")}
        seen_in_batch: set[str] = set()
        accepted: list[SecurityEvent] = []
        errors: list[str] = []
        duplicate_count = 0

        for index, raw in enumerate(records, start=1):
            event_id = str(raw.get("eventId") or "").strip()
            identity_id = str(raw.get("identityId") or "").strip()
            if not event_id or not identity_id:
                errors.append(f"Row {index}: missing eventId or identityId")
                continue
            if identity_id not in known_identity_ids:
                errors.append(f"Row {index}: identityId '{identity_id}' was not found")
                continue
            if event_id in existing_event_ids or event_id in seen_in_batch:
                duplicate_count += 1
                continue

            cloud_service = str(raw.get("cloudService") or raw.get("service") or "").strip()
            action = str(raw.get("action") or "").strip()
            timestamp = str(raw.get("timestampUtc") or raw.get("timestamp") or "").strip()
            if not cloud_service or not action or not timestamp:
                errors.append(f"Row {index}: missing timestampUtc, cloudService, or action")
                continue

            try:
                event = SecurityEvent(
                    eventId=event_id,
                    identityId=identity_id,
                    timestampUtc=timestamp,
                    sourceIp=raw.get("sourceIp"),
                    location=raw.get("location"),
                    cloudService=cloud_service,
                    action=action,
                    resource=str(raw.get("resource", "—")),
                    outcome=str(raw.get("outcome", "success")),
                    sessionId=raw.get("sessionId"),
                    correlationId=raw.get("correlationId"),
                    rawPayload=raw,
                )
            except Exception as exc:  # noqa: BLE001 - surfaced as a per-row rejection, not a 500
                errors.append(f"Row {index}: {exc}")
                continue

            seen_in_batch.add(event_id)
            accepted.append(event)

        if accepted:
            created_at = _now_iso()
            db.executemany(
                "INSERT OR IGNORE INTO security_events (event_id, identity_id, timestamp_utc, source_ip, "
                "location, cloud_service, action, resource, outcome, session_id, correlation_id, "
                "raw_payload, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                [
                    (
                        e.eventId, e.identityId, e.timestampUtc, e.sourceIp, e.location, e.cloudService,
                        e.action, e.resource, e.outcome, e.sessionId, e.correlationId,
                        json.dumps(e.rawPayload), created_at,
                    )
                    for e in accepted
                ],
            )

        return DatasetImportResult(
            acceptedCount=len(accepted), rejectedCount=len(errors), errors=errors[:20],
            duplicateCount=duplicate_count, identitiesCreated=0, identitiesUpdated=0,
            eventsStored=len(accepted),
        )

    def get_latest_baseline(self, identity_id: str) -> IdentityBaseline | None:
        row = db.query_one(
            "SELECT * FROM identity_baselines WHERE identity_id = ? ORDER BY created_at DESC LIMIT 1",
            (identity_id,),
        )
        return _identity_baseline_from_row(row) if row is not None else None

    def get_recent_events_for_identity(self, identity_id: str, limit: int = 25) -> list[SecurityEvent]:
        rows = db.query(
            "SELECT * FROM security_events WHERE identity_id = ? ORDER BY timestamp_utc DESC LIMIT ?",
            (identity_id, limit),
        )
        return [_security_event_from_row(r) for r in rows]

    def get_recent_assessments_for_identity(self, identity_id: str, limit: int = 10) -> list[RiskAssessment]:
        rows = db.query(
            "SELECT ra.response_json FROM risk_assessments ra "
            "JOIN security_events se ON se.event_id = ra.event_id "
            "WHERE se.identity_id = ? ORDER BY ra.created_at DESC LIMIT ?",
            (identity_id, limit),
        )
        return [RiskAssessment.model_validate_json(r["response_json"]) for r in rows]

    def build_identity_profile(
        self, identity_id: str, event_limit: int = 25, assessment_limit: int = 10
    ) -> IdentityProfileResponse | None:
        identity = self.get_identity_by_id(identity_id)
        if identity is None:
            return None
        baseline = self.get_latest_baseline(identity_id)
        events = self.get_recent_events_for_identity(identity_id, event_limit)
        assessments = self.get_recent_assessments_for_identity(identity_id, assessment_limit)
        latest = assessments[0] if assessments else None
        risk_summary = IdentityRiskSummary(
            latestPolicyScore=latest.policyEvaluation.policyScore if latest else None,
            latestAiAdjustment=latest.aiContext.adjustmentApplied if latest else None,
            latestAiStatus=latest.aiContext.status if latest else None,
            latestSeverityFloor=latest.policyEvaluation.severityFloor if latest else None,
            latestFinalRiskScore=latest.calculation.finalRiskScore if latest else None,
            matchedPolicyIds=(
                [r.ruleId for r in latest.policyEvaluation.ruleResults if r.selected and r.state == "matched"]
                if latest else []
            ),
        )
        return IdentityProfileResponse(
            identity=IdentityDetail(
                identityId=identity.identityId,
                name=identity.name,
                identityType=identity.identityType,
                role=identity.role,
                status=identity.status,
                homeTimezone=identity.homeTimezone,
            ),
            baseline=baseline,
            events=events,
            assessments=assessments,
            riskSummary=risk_summary,
        )

    def get_cloud_sources(self) -> tuple[list[CloudSource], int]:
        rows = db.query("SELECT * FROM cloud_sources ORDER BY rowid ASC")
        online = int(_meta("cloud_sources_online") or 0)
        return [_cloud_source_from_row(r) for r in rows], online

    # -- Policies ---------------------------------------------------------

    def get_policies(self) -> list[PolicyRule]:
        rows = db.query("SELECT * FROM policies ORDER BY rowid ASC")
        return [_policy_from_row(r) for r in rows]

    def toggle_policy(self, title: str) -> PolicyRule | None:
        row = db.query_one("SELECT enabled FROM policies WHERE title = ?", (title,))
        if row is None:
            return None
        db.execute("UPDATE policies SET enabled = ? WHERE title = ?", (0 if row["enabled"] else 1, title))
        updated = db.query_one("SELECT * FROM policies WHERE title = ?", (title,))
        return _policy_from_row(updated)

    # -- Risk scoring: security events -------------------------------------

    def insert_security_event(self, event: SecurityEvent) -> SecurityEvent:
        db.execute(
            "INSERT OR IGNORE INTO security_events (event_id, identity_id, timestamp_utc, source_ip, "
            "location, cloud_service, action, resource, outcome, session_id, correlation_id, raw_payload, "
            "created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                event.eventId, event.identityId, event.timestampUtc, event.sourceIp, event.location,
                event.cloudService, event.action, event.resource, event.outcome, event.sessionId,
                event.correlationId, json.dumps(event.rawPayload), _now_iso(),
            ),
        )
        return self.get_security_event(event.eventId)

    def simulate_event_for_identity(self, identity_id: str) -> SecurityEvent:
        """Fabricates one fresh, demo-safe security event for this identity
        right now, so an analyst can immediately run a new assessment and
        see the score respond instead of re-scoring an already-assessed
        event (which is deliberately idempotent, per FR-019)."""
        scenario = random.choice(SIMULATED_EVENT_SCENARIOS)
        event = SecurityEvent(
            eventId=f"EVT-SIM-{uuid4().hex[:12]}",
            identityId=identity_id,
            timestampUtc=_now_iso(),
            sourceIp=scenario["sourceIp"],
            location=scenario["location"],
            cloudService=scenario["cloudService"],
            action=scenario["action"],
            resource=scenario["resource"],
            outcome="success",
        )
        return self.insert_security_event(event)

    def get_security_event(self, event_id: str) -> SecurityEvent | None:
        row = db.query_one("SELECT * FROM security_events WHERE event_id = ?", (event_id,))
        return _security_event_from_row(row) if row is not None else None

    def get_events_for_identity(self, identity_id: str, before_utc: str | None = None) -> list[SecurityEvent]:
        if before_utc is not None:
            rows = db.query(
                "SELECT * FROM security_events WHERE identity_id = ? AND timestamp_utc < ? "
                "ORDER BY timestamp_utc ASC",
                (identity_id, before_utc),
            )
        else:
            rows = db.query(
                "SELECT * FROM security_events WHERE identity_id = ? ORDER BY timestamp_utc ASC",
                (identity_id,),
            )
        return [_security_event_from_row(r) for r in rows]

    def _correlated_sequence(self, event: SecurityEvent) -> list[SecurityEvent]:
        """Bounded same-identity sequence: every event for this identity within
        the preceding SEQUENCE_WINDOW_MINUTES, capped at SEQUENCE_MAX_EVENTS,
        used for both 15-minute frequency counting and compound/sequence
        rules (data-model.md; spec Assumptions)."""
        target = parse_utc(event.timestampUtc)
        start = target - timedelta(minutes=SEQUENCE_WINDOW_MINUTES)
        candidates = self.get_events_for_identity(event.identityId, before_utc=event.timestampUtc)
        window = [e for e in candidates if start <= parse_utc(e.timestampUtc) <= target]
        window.append(event)
        window.sort(key=lambda e: e.timestampUtc)
        return window[-SEQUENCE_MAX_EVENTS:]

    def _get_or_create_baseline(self, identity_id: str, at_time_utc: str):
        history = self.get_events_for_identity(identity_id, before_utc=at_time_utc)
        baseline = build_baseline(identity_id, at_time_utc, history)
        db.execute(
            "INSERT OR IGNORE INTO identity_baselines (baseline_id, identity_id, window_start_utc, "
            "window_end_utc, usual_hours, usual_source_ips, usual_locations, usual_services, usual_actions, "
            "frequency_p95, sample_count, active_day_count, confidence, unknown_fields, baseline_version, "
            "created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                baseline.baselineId, baseline.identityId, baseline.windowStartUtc, baseline.windowEndUtc,
                json.dumps([h.model_dump() for h in baseline.usualHours]),
                json.dumps(baseline.usualSourceIps), json.dumps(baseline.usualLocations),
                json.dumps(baseline.usualServices), json.dumps(baseline.usualActions),
                baseline.frequencyP95, baseline.sampleCount, baseline.activeDayCount, baseline.confidence,
                json.dumps(baseline.unknownFields), baseline.baselineVersion, baseline.createdAt,
            ),
        )
        return baseline

    def _save_policy_evaluation(self, event: SecurityEvent, baseline, snapshot, evaluation) -> None:
        db.execute(
            "INSERT OR IGNORE INTO policy_evaluations (policy_evaluation_id, event_id, baseline_id, "
            "policy_version, policy_snapshot, policy_snapshot_hash, rule_results, policy_score, "
            "severity_floor, severity_floor_minimum, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                evaluation.policyEvaluationId, event.eventId, baseline.baselineId, evaluation.policyVersion,
                json.dumps(snapshot.model_dump()), evaluation.snapshotHash,
                json.dumps([r.model_dump() for r in evaluation.ruleResults]), evaluation.policyScore,
                evaluation.severityFloor, evaluation.severityFloorMinimum, _now_iso(),
            ),
        )

    def _latest_ai_decision(self, cache_key: str) -> tuple[AIContextDecision, int] | None:
        row = db.query_one(
            "SELECT * FROM ai_context_decisions WHERE cache_key = ? ORDER BY refresh_sequence DESC LIMIT 1",
            (cache_key,),
        )
        return (_ai_decision_from_row(row), row["refresh_sequence"]) if row is not None else None

    def _save_ai_decision(
        self, decision: AIContextDecision, cache_key: str, refresh_sequence: int, event_id: str,
        policy_evaluation_id: str,
    ) -> None:
        db.execute(
            "INSERT OR IGNORE INTO ai_context_decisions (ai_decision_id, cache_key, refresh_sequence, "
            "event_id, policy_evaluation_id, adjustment_requested, adjustment_applied, confidence, status, "
            "risk_factors, mitigating_factors, evidence_event_ids, explanation, validation_errors, model, "
            "prompt_version, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                decision.aiDecisionId, cache_key, refresh_sequence, event_id, policy_evaluation_id,
                decision.adjustmentRequested, decision.adjustmentApplied, decision.confidence, decision.status,
                json.dumps(decision.riskFactors), json.dumps(decision.mitigatingFactors),
                json.dumps(decision.evidenceEventIds), decision.explanation,
                json.dumps(decision.validationErrors), decision.model, decision.promptVersion, _now_iso(),
            ),
        )

    def _insert_risk_assessment(self, assessment: RiskAssessment, policy_evaluation_id: str, ai_decision_id: str) -> None:
        db.execute(
            "INSERT OR IGNORE INTO risk_assessments (assessment_id, event_id, policy_evaluation_id, "
            "ai_decision_id, policy_score, ai_adjustment_applied, pre_floor_score, severity_floor, "
            "severity_floor_minimum, final_risk_score, severity, scoring_version, response_json, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                assessment.assessmentId, assessment.eventId, policy_evaluation_id, ai_decision_id,
                assessment.calculation.policyScore, assessment.calculation.aiAdjustmentApplied,
                assessment.calculation.preFloorScore, assessment.policyEvaluation.severityFloor,
                assessment.calculation.severityFloorMinimum, assessment.calculation.finalRiskScore,
                assessment.severity, assessment.scoringVersion, assessment.model_dump_json(),
                assessment.createdAt,
            ),
        )

    def get_risk_assessment(self, assessment_id: str) -> RiskAssessment | None:
        row = db.query_one("SELECT response_json FROM risk_assessments WHERE assessment_id = ?", (assessment_id,))
        return RiskAssessment.model_validate_json(row["response_json"]) if row is not None else None

    def get_risk_assessments_for_event(self, event_id: str) -> list[RiskAssessment]:
        rows = db.query(
            "SELECT response_json FROM risk_assessments WHERE event_id = ? ORDER BY created_at DESC",
            (event_id,),
        )
        return [RiskAssessment.model_validate_json(r["response_json"]) for r in rows]

    def create_risk_assessment(self, event_id: str, force_ai_refresh: bool = False) -> tuple[RiskAssessment, bool]:
        """Runs the full policy + bounded-AI pipeline for an already-stored
        event and persists an immutable assessment. Returns (assessment,
        created) where created=False means an equivalent versioned
        assessment already existed (FR-019 idempotency)."""
        event = self.get_security_event(event_id)
        if event is None:
            raise EventNotFoundError(f"Event '{event_id}' was not found")

        identity = next((i for i in self.get_identities() if i.identityId == event.identityId), None)
        if identity is None:
            raise RiskAssessmentPrerequisiteError(f"Identity '{event.identityId}' could not be resolved")

        baseline = self._get_or_create_baseline(event.identityId, event.timestampUtc)
        sequence = self._correlated_sequence(event)
        snapshot, evaluation = evaluate_policies(event, baseline, sequence, self.get_policies())
        self._save_policy_evaluation(event, baseline, snapshot, evaluation)

        cache_key = f"{event.eventId}|{baseline.baselineId}|{evaluation.snapshotHash}|{PROMPT_VERSION}"
        latest = self._latest_ai_decision(cache_key)
        if force_ai_refresh:
            refresh_sequence = (latest[1] + 1) if latest is not None else 0
            decision = request_ai_decision(event, baseline, evaluation, sequence, cache_key, refresh_sequence)
            self._save_ai_decision(decision, cache_key, refresh_sequence, event.eventId, evaluation.policyEvaluationId)
        elif latest is not None:
            decision, refresh_sequence = latest
        else:
            refresh_sequence = 0
            decision = request_ai_decision(event, baseline, evaluation, sequence, cache_key, refresh_sequence)
            self._save_ai_decision(decision, cache_key, refresh_sequence, event.eventId, evaluation.policyEvaluationId)

        calculation, severity = calculate_risk(
            evaluation.policyScore, decision.adjustmentApplied, evaluation.severityFloorMinimum
        )
        assessment_id = "risk-" + sha256(
            f"{event.eventId}|{evaluation.policyEvaluationId}|{decision.aiDecisionId}|{SCORING_VERSION}".encode()
        ).hexdigest()[:24]

        existing = self.get_risk_assessment(assessment_id)
        if existing is not None:
            self._sync_identity_from_assessment(event, existing)
            return existing, False

        assessment = RiskAssessment(
            assessmentId=assessment_id,
            eventId=event.eventId,
            baseline=RiskBaselineRef(baselineId=baseline.baselineId, confidence=baseline.confidence),
            policyEvaluation=evaluation,
            aiContext=decision,
            calculation=calculation,
            severity=severity,
            scoringVersion=SCORING_VERSION,
            createdAt=_now_iso(),
        )
        self._insert_risk_assessment(assessment, evaluation.policyEvaluationId, decision.aiDecisionId)
        self._sync_identity_from_assessment(event, assessment)
        return assessment, True

    def _sync_identity_from_assessment(self, event: SecurityEvent, assessment: RiskAssessment) -> None:
        """Keeps the legacy identity-card score/activity fields (still shown
        on the Identity Profiles grid) in step with the latest real
        assessment, but only when this event is that identity's most recent
        one — an out-of-order re-assessment of an older event must not
        overwrite a newer card state."""
        latest_event_row = db.query_one(
            "SELECT event_id FROM security_events WHERE identity_id = ? ORDER BY timestamp_utc DESC LIMIT 1",
            (event.identityId,),
        )
        if latest_event_row is not None and latest_event_row["event_id"] != event.eventId:
            return
        matched = [
            r.ruleId for r in assessment.policyEvaluation.ruleResults if r.selected and r.state == "matched"
        ]
        activity = f"{assessment.severity} risk ({assessment.calculation.finalRiskScore}): " + (
            ", ".join(matched) if matched else "no policy matches"
        )
        db.execute(
            "UPDATE identities SET score = ?, activity = ?, last_seen_at = ? WHERE identity_id = ?",
            (assessment.calculation.finalRiskScore, activity[:240], event.timestampUtc, event.identityId),
        )

    # -- Reports ------------------------------------------------------------

    def get_reports(self) -> list[ReportTemplate]:
        rows = db.query("SELECT * FROM reports ORDER BY rowid ASC")
        return [_report_from_row(r) for r in rows]

    def get_report(self, title: str) -> ReportTemplate | None:
        row = db.query_one("SELECT * FROM reports WHERE title = ?", (title,))
        return _report_from_row(row) if row is not None else None

    # -- Configuration ----------------------------------------------------

    def get_configuration(self) -> Configuration:
        row = db.query_one("SELECT * FROM configuration")
        return Configuration(
            notificationsEnabled=bool(row["notifications_enabled"]),
            plainLanguageExplanations=bool(row["plain_language_explanations"]),
        )

    def set_configuration(self, config: Configuration) -> Configuration:
        db.execute(
            "UPDATE configuration SET notifications_enabled = ?, plain_language_explanations = ?",
            (int(config.notificationsEnabled), int(config.plainLanguageExplanations)),
        )
        return config

    # -- Seed-only singleton values (queried live; never mutated at runtime) --

    @property
    def model_rationale(self) -> ModelRationale:
        row = db.query_one("SELECT * FROM model_rationale")
        return ModelRationale(
            topFindingId=row["top_finding_id"],
            explanation=row["explanation"],
            signals=[RationaleSignal(**s) for s in json.loads(row["signals"])],
        )

    @property
    def access_trend(self) -> list[AccessTrendPoint]:
        rows = db.query("SELECT * FROM access_trend ORDER BY id ASC")
        return [AccessTrendPoint(label=r["label"], events=r["events"], anomalies=r["anomalies"]) for r in rows]

    @property
    def access_trend_peak_label(self) -> str:
        return _meta("access_trend_peak_label")

    @property
    def service_risk(self) -> list[ServiceRisk]:
        rows = db.query("SELECT * FROM service_risk ORDER BY id ASC")
        return [ServiceRisk(name=r["name"], risk=r["risk"], events=r["events"]) for r in rows]

    @property
    def service_risk_summary(self) -> ServiceRiskSummary:
        row = db.query_one("SELECT * FROM service_risk_summary")
        return ServiceRiskSummary(
            highestRiskService=row["highest_risk_service"],
            sensitiveAssets=row["sensitive_assets"],
            coverage=row["coverage"],
        )

    @property
    def findings(self) -> list[Finding]:
        return self.get_findings()

    @property
    def identities(self) -> list[Identity]:
        return self.get_identities()

    @property
    def policies(self) -> list[PolicyRule]:
        return self.get_policies()


_store: Store | None = None


def get_store() -> Store:
    global _store
    if _store is None:
        is_fresh = db.query_one("SELECT COUNT(*) AS n FROM findings")["n"] == 0
        if is_fresh:
            seed_database()
        _store = Store()
    return _store


def reset_for_tests() -> None:
    """Drop the SQLite connection and the Store singleton so the next
    get_store() call reseeds from scratch, simulating a fresh backend
    start within one test process. Test-only helper."""
    global _store
    db.reset_for_tests()
    _store = None
