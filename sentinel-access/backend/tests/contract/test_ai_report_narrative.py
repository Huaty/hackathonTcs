from fastapi.testclient import TestClient

from app.main import app
from app.routers import reports

client = TestClient(app)


def test_prepare_report_includes_narrative(monkeypatch):
    def fake_call_chat_completions(messages, tools=None):
        return {"content": "Today's activity showed a handful of findings worth review."}

    monkeypatch.setattr(reports, "call_chat_completions", fake_call_chat_completions)

    report_title = client.get("/api/reports").json()["reports"][0]["title"]
    response = client.post(f"/api/reports/{report_title}/prepare")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready"
    assert body["narrative"] == "Today's activity showed a handful of findings worth review."


def test_prepare_report_404():
    response = client.post("/api/reports/does-not-exist/prepare")
    assert response.status_code == 404
