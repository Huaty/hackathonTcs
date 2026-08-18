import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import store as store_module
from app.main import app

SEED_FILE = Path(__file__).resolve().parents[3] / "server" / "data" / "synthetic-data.json"


@pytest.fixture()
def fresh_client():
    """Simulate a fresh backend start within this test process: drop the
    SQLite connection and Store singleton so the next get_store() call
    reseeds from server/data/synthetic-data.json, per 003-sqlite-storage
    User Story 1 (storage swap must be behavior-preserving)."""
    store_module.reset_for_tests()
    yield TestClient(app)
    store_module.reset_for_tests()


@pytest.fixture()
def seed_raw():
    return json.loads(SEED_FILE.read_text(encoding="utf-8"))


def test_command_center_matches_seed_on_fresh_start(fresh_client, seed_raw):
    body = fresh_client.get("/api/command-center").json()

    assert body["findings"] == seed_raw["alerts"]
    assert body["modelRationale"]["topFindingId"] == seed_raw["modelRationale"]["topFindingId"]
    assert body["modelRationale"]["explanation"] == seed_raw["modelRationale"]["explanation"]
    assert body["modelRationale"]["signals"] == seed_raw["modelRationale"]["signals"]
    assert body["accessTrend"] == seed_raw["accessTrend"]
    assert body["accessTrendPeakLabel"] == seed_raw["accessTrendPeakLabel"]
    assert body["serviceRisk"] == seed_raw["serviceRisk"]
    assert body["serviceRiskSummary"] == seed_raw["serviceRiskSummary"]

    metrics = body["summaryMetrics"]
    assert metrics["mostUrgentCase"]["label"] == seed_raw["alerts"][0]["title"]
    assert metrics["needsAttention"] == len(seed_raw["alerts"])
    assert metrics["averageReviewTime"] == seed_raw["summaryMetrics"]["averageReviewTime"]
    assert metrics["signalConfidencePct"] == seed_raw["summaryMetrics"]["signalConfidencePct"]
    assert metrics["identityCoveragePct"] == seed_raw["summaryMetrics"]["identityCoveragePct"]
    # Deliberate exception (003-sqlite-storage FR-009): activitiesChecked is
    # now a live count of activity_log rows, not the seed file's separate
    # static demo constant (1482) — see data-model.md "Changed behavior 2".
    assert metrics["activitiesChecked"] == len(seed_raw["activityLog"])


def test_activity_identities_estate_match_seed_on_fresh_start(fresh_client, seed_raw):
    activity = fresh_client.get("/api/activity").json()
    assert activity["source"] == "seed"
    assert activity["events"] == seed_raw["activityLog"]

    identities = fresh_client.get("/api/identities").json()["identities"]
    # Identity Profiles are now database-backed with an additive stable
    # identityId plus profile fields (004-contextual-risk-scoring FR-001,
    # FR-020); existing seed-sourced UI card fields must still match exactly.
    for actual, seed in zip(identities, seed_raw["identities"]):
        for key in seed:
            assert actual[key] == seed[key]
        assert actual["identityId"]

    estate = fresh_client.get("/api/estate").json()
    assert estate["sources"] == seed_raw["cloudSources"]
    assert estate["sourcesOnline"] == seed_raw["cloudSourcesOnline"]


def test_policies_reports_configuration_match_seed_on_fresh_start(fresh_client, seed_raw):
    policies = fresh_client.get("/api/policies").json()["policies"]
    # Policy Catalog v1 rows are additive over the prior title/description/
    # enabled/category shape (004-contextual-risk-scoring FR-005); updatedAt
    # is DB provenance only and is not part of the API response shape.
    for actual, seed in zip(policies, seed_raw["policies"]):
        for key in seed:
            if key == "updatedAt":
                continue
            assert actual[key] == seed[key]

    reports = fresh_client.get("/api/reports").json()["reports"]
    assert reports == seed_raw["reports"]

    configuration = fresh_client.get("/api/configuration").json()
    assert configuration == {"notificationsEnabled": True, "plainLanguageExplanations": True}


def test_mutations_persist_across_reads_on_sqlite_store(fresh_client, seed_raw):
    """US1 Acceptance Scenarios 2-3: finding status, policy toggle, and
    configuration changes must persist for the rest of the run, the same
    as the pre-migration in-memory list Store."""
    finding_id = seed_raw["alerts"][0]["id"]
    status_response = fresh_client.post(f"/api/findings/{finding_id}/status", json={"status": "in_progress"})
    assert status_response.status_code == 200
    assert fresh_client.get(f"/api/findings/{finding_id}").json()["status"] == "in_progress"

    policy_title = seed_raw["policies"][0]["title"]
    before_enabled = seed_raw["policies"][0]["enabled"]
    toggle_response = fresh_client.post(f"/api/policies/{policy_title}/toggle")
    assert toggle_response.status_code == 200
    assert toggle_response.json()["enabled"] != before_enabled
    policies_after = fresh_client.get("/api/policies").json()["policies"]
    toggled = next(p for p in policies_after if p["title"] == policy_title)
    assert toggled["enabled"] != before_enabled

    config_response = fresh_client.put(
        "/api/configuration", json={"notificationsEnabled": False, "plainLanguageExplanations": False}
    )
    assert config_response.status_code == 200
    assert fresh_client.get("/api/configuration").json() == {
        "notificationsEnabled": False,
        "plainLanguageExplanations": False,
    }


def test_report_preparation_still_works_after_storage_swap(fresh_client, seed_raw):
    """Covers FR-004's inclusion of report preparation among the mutation
    endpoints that must keep working unchanged (speckit-analyze finding F4)."""
    title = seed_raw["reports"][0]["title"]
    response = fresh_client.post(f"/api/reports/{title}/prepare")
    assert response.status_code == 200
    body = response.json()
    assert body["title"] == title
    assert body["status"] == "ready"
