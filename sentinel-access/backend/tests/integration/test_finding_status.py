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
