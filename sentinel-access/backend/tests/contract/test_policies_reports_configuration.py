from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_get_policies_shape():
    response = client.get("/api/policies")
    assert response.status_code == 200
    assert len(response.json()["policies"]) > 0


def test_toggle_policy_404():
    response = client.post("/api/policies/does-not-exist/toggle")
    assert response.status_code == 404


def test_toggle_policy_flips_state():
    title = client.get("/api/policies").json()["policies"][0]["title"]
    before = client.get("/api/policies").json()["policies"][0]["enabled"]
    response = client.post(f"/api/policies/{title}/toggle")
    assert response.status_code == 200
    assert response.json()["enabled"] != before
    client.post(f"/api/policies/{title}/toggle")  # restore original state


def test_get_reports_shape():
    response = client.get("/api/reports")
    assert response.status_code == 200
    assert len(response.json()["reports"]) > 0


def test_prepare_report_404():
    response = client.post("/api/reports/does-not-exist/prepare")
    assert response.status_code == 404


def test_prepare_report_200():
    title = client.get("/api/reports").json()["reports"][0]["title"]
    response = client.post(f"/api/reports/{title}/prepare")
    assert response.status_code == 200
    assert response.json()["status"] == "ready"


def test_export_activity_csv():
    response = client.get("/api/reports/export.csv")
    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]
    assert "Time,Actor,Action,Source,System,Status" in response.text


def test_get_and_put_configuration():
    get_response = client.get("/api/configuration")
    assert get_response.status_code == 200

    put_response = client.put(
        "/api/configuration",
        json={"notificationsEnabled": False, "plainLanguageExplanations": False},
    )
    assert put_response.status_code == 200
    assert put_response.json() == {"notificationsEnabled": False, "plainLanguageExplanations": False}

    # restore defaults
    client.put(
        "/api/configuration",
        json={"notificationsEnabled": True, "plainLanguageExplanations": True},
    )
