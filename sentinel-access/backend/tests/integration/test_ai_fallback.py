"""Verifies all three AI-backed endpoints degrade gracefully (FR-007) when
the liteLLM proxy is unreachable — never a 5xx, always a documented fallback."""

from fastapi.testclient import TestClient

from app.ai_client import AIServiceError
from app.main import app
from app.routers import command_center, copilot, reports

client = TestClient(app)


def _raise_ai_service_error(*args, **kwargs):
    raise AIServiceError("liteLLM proxy unreachable")


def test_finding_explanation_falls_back(monkeypatch):
    monkeypatch.setattr(command_center, "call_chat_completions", _raise_ai_service_error)

    findings = client.get("/api/command-center").json()["findings"]
    finding_id = findings[0]["id"]

    response = client.get(f"/api/findings/{finding_id}/explanation")
    assert response.status_code == 200
    body = response.json()
    assert body["source"] == "fallback"
    assert body["explanation"]  # non-empty — the finding's description/baseline


def test_copilot_falls_back(monkeypatch):
    monkeypatch.setattr(copilot, "call_chat_completions", _raise_ai_service_error)

    response = client.post("/api/copilot/query", json={"question": "show me high-risk findings"})
    assert response.status_code == 200
    body = response.json()
    assert "unavailable" in body["answer"].lower()
    assert body["findings"] == []
    assert body["activity"] == []
    assert body["identities"] == []


def test_report_prepare_falls_back(monkeypatch):
    monkeypatch.setattr(reports, "call_chat_completions", _raise_ai_service_error)

    report_title = client.get("/api/reports").json()["reports"][0]["title"]
    response = client.post(f"/api/reports/{report_title}/prepare")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready"  # non-AI confirmation still succeeds
    assert body["narrative"] is None
