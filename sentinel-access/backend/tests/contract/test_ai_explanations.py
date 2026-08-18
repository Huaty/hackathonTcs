from fastapi.testclient import TestClient

from app.main import app
from app.routers import command_center

client = TestClient(app)


def test_get_explanation_404():
    response = client.get("/api/findings/DOES-NOT-EXIST/explanation")
    assert response.status_code == 404


def test_get_explanation_generated_and_cached(monkeypatch):
    findings = client.get("/api/command-center").json()["findings"]
    finding_id = findings[0]["id"]

    calls = {"count": 0}

    def fake_call_chat_completions(messages, tools=None):
        calls["count"] += 1
        return {"content": "This finding was flagged because of X and Y."}

    monkeypatch.setattr(command_center, "call_chat_completions", fake_call_chat_completions)

    first = client.get(f"/api/findings/{finding_id}/explanation")
    assert first.status_code == 200
    body = first.json()
    assert body["findingId"] == finding_id
    assert body["source"] == "ai"
    assert body["explanation"] == "This finding was flagged because of X and Y."
    assert calls["count"] == 1

    second = client.get(f"/api/findings/{finding_id}/explanation")
    assert second.status_code == 200
    assert second.json()["explanation"] == first.json()["explanation"]
    assert calls["count"] == 1  # not regenerated on repeat view
