from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_start_investigation_persists_across_refetch():
    findings = client.get("/api/command-center").json()["findings"]
    finding_id = findings[0]["id"]

    post_response = client.post(f"/api/findings/{finding_id}/status", json={"status": "in_progress"})
    assert post_response.status_code == 200
    assert post_response.json()["status"] == "in_progress"

    refetched = client.get(f"/api/findings/{finding_id}")
    assert refetched.status_code == 200
    assert refetched.json()["status"] == "in_progress"

    queue = client.get("/api/command-center").json()["findings"]
    updated = next(f for f in queue if f["id"] == finding_id)
    assert updated["status"] == "in_progress"


def test_simulate_anomaly_increases_needs_attention_kpi():
    before = client.get("/api/command-center").json()["summaryMetrics"]["needsAttention"]
    client.post("/api/findings/simulate-anomaly")
    after = client.get("/api/command-center").json()["summaryMetrics"]["needsAttention"]
    assert after == before + 1


def test_escalating_a_finding_removes_it_from_needs_attention():
    created = client.post("/api/findings/simulate-anomaly").json()
    before = client.get("/api/command-center").json()["summaryMetrics"]["needsAttention"]

    client.post(f"/api/findings/{created['id']}/status", json={"status": "escalated"})

    after = client.get("/api/command-center").json()["summaryMetrics"]["needsAttention"]
    assert after == before - 1


def test_most_urgent_case_tracks_highest_scoring_active_finding():
    findings = client.get("/api/command-center").json()["findings"]
    active = [f for f in findings if f["status"] != "escalated"]
    expected_top = max(active, key=lambda f: f["score"])

    metrics = client.get("/api/command-center").json()["summaryMetrics"]
    assert metrics["mostUrgentCase"]["label"] == expected_top["title"]
