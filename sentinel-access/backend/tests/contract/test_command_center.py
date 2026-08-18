from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_get_command_center_shape():
    response = client.get("/api/command-center")
    assert response.status_code == 200
    body = response.json()
    assert "summaryMetrics" in body
    assert "findings" in body
    assert "modelRationale" in body
    assert "accessTrend" in body
    assert "serviceRisk" in body


def test_get_finding_404():
    response = client.get("/api/findings/DOES-NOT-EXIST")
    assert response.status_code == 404


def test_get_finding_200():
    findings = client.get("/api/command-center").json()["findings"]
    finding_id = findings[0]["id"]
    response = client.get(f"/api/findings/{finding_id}")
    assert response.status_code == 200
    assert response.json()["id"] == finding_id


def test_update_finding_status_invalid_value():
    findings = client.get("/api/command-center").json()["findings"]
    finding_id = findings[0]["id"]
    response = client.post(f"/api/findings/{finding_id}/status", json={"status": "bogus"})
    assert response.status_code == 422


def test_simulate_anomaly_returns_created_finding():
    response = client.post("/api/findings/simulate-anomaly")
    assert response.status_code == 201
    assert response.json()["id"].startswith("ALT-SIM-")
