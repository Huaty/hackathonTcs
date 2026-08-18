import json

from fastapi.testclient import TestClient

from app.main import app
from app.routers import copilot

client = TestClient(app)


def test_copilot_query_no_tool_call(monkeypatch):
    def fake_call_chat_completions(messages, tools=None):
        return {"content": "I can only answer questions about the current security data."}

    monkeypatch.setattr(copilot, "call_chat_completions", fake_call_chat_completions)

    response = client.post("/api/copilot/query", json={"question": "what is the capital of France"})
    assert response.status_code == 200
    body = response.json()
    assert body["answer"]
    assert body["findings"] == []
    assert body["activity"] == []
    assert body["identities"] == []


def test_copilot_query_with_tool_call(monkeypatch):
    responses = [
        {
            "content": None,
            "tool_calls": [
                {
                    "id": "call_1",
                    "function": {"name": "filter_findings", "arguments": json.dumps({})},
                }
            ],
        },
        {"content": "Here are the matching findings."},
    ]

    def fake_call_chat_completions(messages, tools=None):
        return responses.pop(0)

    monkeypatch.setattr(copilot, "call_chat_completions", fake_call_chat_completions)

    response = client.post("/api/copilot/query", json={"question": "show me all findings"})
    assert response.status_code == 200
    body = response.json()
    assert body["answer"] == "Here are the matching findings."
    assert len(body["findings"]) > 0
    assert body["activity"] == []
    assert body["identities"] == []


def test_copilot_query_empty_question_rejected():
    response = client.post("/api/copilot/query", json={})
    assert response.status_code == 422
