from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_get_activity_shape():
    response = client.get("/api/activity")
    assert response.status_code == 200
    body = response.json()
    assert "events" in body
    assert body["source"] in ("seed", "imported")


def test_get_activity_search_filter():
    response = client.get("/api/activity", params={"search": "aisha"})
    assert response.status_code == 200
    events = response.json()["events"]
    assert all("aisha" in e["actor"].lower() for e in events)


def test_get_identities_shape():
    response = client.get("/api/identities")
    assert response.status_code == 200
    assert len(response.json()["identities"]) > 0


def test_get_identity_timeline_404():
    response = client.get("/api/identities/does-not-exist/timeline")
    assert response.status_code == 404


def test_get_identity_timeline_200():
    name = client.get("/api/identities").json()["identities"][0]["name"]
    response = client.get(f"/api/identities/{name}/timeline")
    assert response.status_code == 200
    assert "events" in response.json()


def test_get_estate_shape():
    response = client.get("/api/estate")
    assert response.status_code == 200
    body = response.json()
    assert "sources" in body
    assert "sourcesOnline" in body
