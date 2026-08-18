import datetime

from fastapi.testclient import TestClient

from app.ai_client import AIServiceError
from app.main import app
from app.schemas.entities import SecurityEvent
from app.services import ai_risk_context
from app.store import get_store

client = TestClient(app)
store = get_store()
IDENTITY_ID = store.get_identities()[0].identityId


def _seed_baseline_history(prefix: str, service="s3", action="GetObject", days=8, per_day=3):
    # Within the 30-day window before the 2026-08-01T09:05:00Z target events
    # used throughout this file, so baselines reach "high" confidence
    # (>=20 events, >=7 active days) per FR-004.
    base = datetime.datetime(2026, 7, 5, 9, 0, tzinfo=datetime.timezone.utc)
    for d in range(days):
        for k in range(per_day):
            t = base + datetime.timedelta(days=d, minutes=k * 5)
            store.insert_security_event(
                SecurityEvent(
                    eventId=f"EVT-{prefix}-HIST-{d}-{k}",
                    identityId=IDENTITY_ID,
                    timestampUtc=t.isoformat().replace("+00:00", "Z"),
                    sourceIp="10.0.0.5",
                    location="US",
                    cloudService=service,
                    action=action,
                    resource="bucket/x",
                    outcome="success",
                )
            )


def _target_event(event_id: str, **overrides) -> SecurityEvent:
    fields = dict(
        eventId=event_id,
        identityId=IDENTITY_ID,
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


def test_create_risk_assessment_404_for_unknown_event():
    response = client.post("/api/risk-assessments", json={"eventId": "EVT-DOES-NOT-EXIST"})
    assert response.status_code == 404


def test_create_risk_assessment_409_for_unresolved_identity(monkeypatch):
    monkeypatch.setattr(
        ai_risk_context, "call_risk_context", lambda messages: (_ for _ in ()).throw(AIServiceError("no proxy"))
    )
    store.insert_security_event(
        _target_event("EVT-ORPHAN", identityId="id-does-not-exist")
    )
    response = client.post("/api/risk-assessments", json={"eventId": "EVT-ORPHAN"})
    assert response.status_code == 409


def test_normal_event_matches_no_rules_and_applies_zero_adjustment(monkeypatch):
    monkeypatch.setattr(
        ai_risk_context, "call_risk_context", lambda messages: (_ for _ in ()).throw(AIServiceError("no proxy"))
    )
    _seed_baseline_history("NORMAL")
    store.insert_security_event(_target_event("EVT-NORMAL-1", timestampUtc="2026-08-01T09:05:00Z"))

    response = client.post("/api/risk-assessments", json={"eventId": "EVT-NORMAL-1"})
    assert response.status_code == 201
    body = response.json()

    assert body["policyEvaluation"]["policyScore"] == 0
    assert body["policyEvaluation"]["severityFloor"] is None
    assert all(r["awardedPoints"] == 0 for r in body["policyEvaluation"]["ruleResults"])
    assert body["aiContext"]["status"] == "unavailable"
    assert body["aiContext"]["adjustmentApplied"] == 0
    assert body["calculation"]["finalRiskScore"] == 0
    assert body["severity"] == "Low"
    assert body["scoringVersion"] == "policy-ai-risk-v1"
    assert body["policyEvaluation"]["policyVersion"] == "policy-catalog-v1"


def test_policy_and_ai_adjustment_arithmetic_and_evidence(monkeypatch):
    def fake_call_risk_context(messages):
        return (
            {
                "adjustment": 10,
                "confidence": 0.9,
                "riskFactors": ["Correlated privilege pivot"],
                "mitigatingFactors": [],
                "evidenceEventIds": ["EVT-ADJ-1"],
                "explanation": "Escalation supported by evidence.",
            },
            "test-model",
        )

    monkeypatch.setattr(ai_risk_context, "call_risk_context", fake_call_risk_context)
    _seed_baseline_history("ADJ")
    store.insert_security_event(
        _target_event(
            "EVT-ADJ-1",
            timestampUtc="2026-08-01T09:05:00Z",
            sourceIp="203.0.113.9",
            location="DE",
            cloudService="iam",
            action="Grant Administrator Role",
        )
    )

    response = client.post("/api/risk-assessments", json={"eventId": "EVT-ADJ-1"})
    assert response.status_code == 201
    body = response.json()

    calc = body["calculation"]
    assert calc["policyScore"] == 90
    assert calc["aiAdjustmentApplied"] == 10
    assert calc["preFloorScore"] == min(100, 90 + 10)
    assert calc["severityFloorMinimum"] == 65
    assert calc["finalRiskScore"] == max(calc["preFloorScore"], 65)
    assert body["severity"] == "Critical"
    assert body["aiContext"]["status"] == "applied"
    assert body["aiContext"]["evidenceEventIds"] == ["EVT-ADJ-1"]
    assert body["aiContext"]["promptVersion"] == "risk-context-prompt-v1"


def test_negative_ai_adjustment_cannot_bypass_severity_floor(monkeypatch):
    def fake_call_risk_context(messages):
        return (
            {
                "adjustment": -15,
                "confidence": 0.9,
                "riskFactors": [],
                "mitigatingFactors": ["Change was part of an approved maintenance window"],
                "evidenceEventIds": ["EVT-FLOOR-1"],
                "explanation": "Mitigated by change ticket.",
            },
            "test-model",
        )

    monkeypatch.setattr(ai_risk_context, "call_risk_context", fake_call_risk_context)
    _seed_baseline_history("FLOOR")
    store.insert_security_event(
        _target_event(
            "EVT-FLOOR-1",
            timestampUtc="2026-08-01T09:05:00Z",
            cloudService="logging",
            action="Disable Logging Trail",
        )
    )

    response = client.post("/api/risk-assessments", json={"eventId": "EVT-FLOOR-1"})
    assert response.status_code == 201
    body = response.json()

    assert body["policyEvaluation"]["severityFloor"] == "High"
    assert body["calculation"]["severityFloorMinimum"] == 65
    assert body["calculation"]["aiAdjustmentApplied"] == -15
    assert body["calculation"]["finalRiskScore"] >= 65
    assert body["severity"] in ("High", "Critical")


def test_low_confidence_ai_adjustment_is_applied_as_zero(monkeypatch):
    def fake_call_risk_context(messages):
        return (
            {
                "adjustment": 10,
                "confidence": 0.4,
                "riskFactors": ["Weak signal"],
                "mitigatingFactors": [],
                "evidenceEventIds": ["EVT-LOWCONF-1"],
                "explanation": "Low confidence context.",
            },
            "test-model",
        )

    monkeypatch.setattr(ai_risk_context, "call_risk_context", fake_call_risk_context)
    _seed_baseline_history("LOWCONF")
    store.insert_security_event(_target_event("EVT-LOWCONF-1", timestampUtc="2026-08-01T09:05:00Z"))

    response = client.post("/api/risk-assessments", json={"eventId": "EVT-LOWCONF-1"})
    assert response.status_code == 201
    body = response.json()

    assert body["aiContext"]["status"] == "low_confidence"
    assert body["aiContext"]["adjustmentApplied"] == 0
    assert body["calculation"]["aiAdjustmentApplied"] == 0


def test_repeat_assessment_is_idempotent_and_returns_200(monkeypatch):
    monkeypatch.setattr(
        ai_risk_context, "call_risk_context", lambda messages: (_ for _ in ()).throw(AIServiceError("no proxy"))
    )
    _seed_baseline_history("IDEMP")
    store.insert_security_event(_target_event("EVT-IDEMP-1", timestampUtc="2026-08-01T09:05:00Z"))

    first = client.post("/api/risk-assessments", json={"eventId": "EVT-IDEMP-1"})
    assert first.status_code == 201
    second = client.post("/api/risk-assessments", json={"eventId": "EVT-IDEMP-1"})
    assert second.status_code == 200
    assert second.json()["assessmentId"] == first.json()["assessmentId"]


def test_get_risk_assessment_by_id_and_by_event(monkeypatch):
    monkeypatch.setattr(
        ai_risk_context, "call_risk_context", lambda messages: (_ for _ in ()).throw(AIServiceError("no proxy"))
    )
    _seed_baseline_history("LOOKUP")
    store.insert_security_event(_target_event("EVT-LOOKUP-1", timestampUtc="2026-08-01T09:05:00Z"))
    created = client.post("/api/risk-assessments", json={"eventId": "EVT-LOOKUP-1"}).json()

    by_id = client.get(f"/api/risk-assessments/{created['assessmentId']}")
    assert by_id.status_code == 200
    assert by_id.json()["assessmentId"] == created["assessmentId"]

    by_event = client.get("/api/events/EVT-LOOKUP-1/risk-assessments")
    assert by_event.status_code == 200
    assert len(by_event.json()["assessments"]) == 1

    missing = client.get("/api/risk-assessments/risk-does-not-exist")
    assert missing.status_code == 404
