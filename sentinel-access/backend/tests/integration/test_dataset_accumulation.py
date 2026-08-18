from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import store as store_module
from app.main import app

DATASET_FILE = Path(__file__).resolve().parents[4] / "datasets" / "synthetic-data.json"


@pytest.fixture()
def fresh_client():
    """Fresh backend start within this process, per 003-sqlite-storage
    Stories 2 & 3: activity uploads must accumulate on top of a known
    starting point, not an arbitrary one left over from earlier tests."""
    store_module.reset_for_tests()
    yield TestClient(app)
    store_module.reset_for_tests()


def _upload_dataset_file(client: TestClient):
    content = DATASET_FILE.read_text(encoding="utf-8")
    return client.post("/api/datasets", files={"file": ("synthetic-data.json", content, "application/json")})


def test_three_sequential_uploads_accumulate_without_losing_prior_rows(fresh_client):
    """spec.md SC-002/SC-004: accumulation must be verified across at
    least 3 consecutive uploads in the same run, with every prior row
    (seed + earlier uploads) still present and unchanged afterward. Also
    covers US3/FR-009: activitiesChecked must track the same total live."""
    seed_events = fresh_client.get("/api/activity").json()["events"]
    seed_count = len(seed_events)
    assert fresh_client.get("/api/command-center").json()["summaryMetrics"]["activitiesChecked"] == seed_count

    running_total = seed_count
    for _ in range(3):
        response = _upload_dataset_file(fresh_client)
        assert response.status_code == 200
        body = response.json()
        assert body["acceptedCount"] == 8  # 8 valid records; the file's 9th entry is an empty object
        assert body["rejectedCount"] == 1

        running_total += body["acceptedCount"]
        events = fresh_client.get("/api/activity").json()["events"]
        assert len(events) == running_total
        # every prior row (seed rows included) is still present, unchanged, at the front
        assert events[:seed_count] == seed_events

        activities_checked = fresh_client.get("/api/command-center").json()["summaryMetrics"]["activitiesChecked"]
        assert activities_checked == running_total


def test_failed_upload_leaves_activity_log_completely_unchanged(fresh_client):
    """spec.md US2 Acceptance Scenario 4 / FR-007 / SC-003, and US3
    Acceptance Scenario 3: activitiesChecked must also stay unchanged."""
    before = fresh_client.get("/api/activity").json()["events"]
    before_metrics = fresh_client.get("/api/command-center").json()["summaryMetrics"]["activitiesChecked"]

    response = fresh_client.post(
        "/api/datasets", files={"file": ("bad.json", "{not valid json", "application/json")}
    )
    assert response.status_code == 400

    after = fresh_client.get("/api/activity").json()["events"]
    assert after == before
    after_metrics = fresh_client.get("/api/command-center").json()["summaryMetrics"]["activitiesChecked"]
    assert after_metrics == before_metrics


def test_upload_does_not_touch_other_entities(fresh_client):
    """FR-010: dataset upload must not create/modify findings, identities,
    policies, cloud sources, or reports."""
    before_findings = fresh_client.get("/api/command-center").json()["findings"]
    before_identities = fresh_client.get("/api/identities").json()["identities"]
    before_policies = fresh_client.get("/api/policies").json()["policies"]
    before_estate = fresh_client.get("/api/estate").json()
    before_reports = fresh_client.get("/api/reports").json()["reports"]

    response = _upload_dataset_file(fresh_client)
    assert response.status_code == 200

    assert fresh_client.get("/api/command-center").json()["findings"] == before_findings
    assert fresh_client.get("/api/identities").json()["identities"] == before_identities
    assert fresh_client.get("/api/policies").json()["policies"] == before_policies
    assert fresh_client.get("/api/estate").json() == before_estate
    assert fresh_client.get("/api/reports").json()["reports"] == before_reports


def test_upload_does_not_change_needs_attention_or_most_urgent_case(fresh_client):
    """FR-011: needsAttention/mostUrgentCase derive solely from findings
    and must be unaffected by dataset uploads."""
    before_metrics = fresh_client.get("/api/command-center").json()["summaryMetrics"]

    response = _upload_dataset_file(fresh_client)
    assert response.status_code == 200

    after_metrics = fresh_client.get("/api/command-center").json()["summaryMetrics"]
    assert after_metrics["needsAttention"] == before_metrics["needsAttention"]
    assert after_metrics["mostUrgentCase"] == before_metrics["mostUrgentCase"]
