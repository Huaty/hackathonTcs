import json

from fastapi import APIRouter, Depends

from app.ai_client import AIServiceError, call_chat_completions
from app.schemas.entities import ActivityEvent, CopilotQueryRequest, CopilotResponse, Finding, Identity
from app.store import Store, get_store

router = APIRouter(prefix="/api", tags=["copilot"])

_UNAVAILABLE_ANSWER = "The AI assistant is unavailable right now — try the search and filter controls instead."

_SYSTEM_PROMPT = (
    "You are Ask Sentinel, an assistant for a security analyst working in the "
    "Sentinel Access dashboard. Answer only using the provided tools, which "
    "read the analyst's current findings, activity log, and identities. "
    "Never invent findings, activity, or identities that the tools did not "
    "return. If a question is unrelated to this security data, politely "
    "decline and say you can only answer questions about the current "
    "security data. If a tool call returns no matching records, say so "
    "plainly rather than guessing."
)

_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "filter_findings",
            "description": "Look up findings (investigation queue) by service, minimum risk score, and/or status.",
            "parameters": {
                "type": "object",
                "properties": {
                    "service": {"type": "string", "description": "Cloud service name, e.g. 'AWS IAM'"},
                    "min_score": {"type": "integer", "description": "Minimum risk score (0-100)"},
                    "status": {"type": "string", "enum": ["open", "in_progress", "escalated"]},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "filter_activity",
            "description": "Look up activity log events by free-text search and/or status.",
            "parameters": {
                "type": "object",
                "properties": {
                    "search": {"type": "string", "description": "Free-text search over actor/action/source/system"},
                    "status": {"type": "string", "enum": ["Needs attention", "Review later", "Normal"]},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "filter_identities",
            "description": "Look up identities by minimum risk score.",
            "parameters": {
                "type": "object",
                "properties": {
                    "min_score": {"type": "integer", "description": "Minimum risk score (0-100)"},
                },
            },
        },
    },
]


def _filter_findings(store: Store, service: str | None = None, min_score: int | None = None, status: str | None = None) -> list[Finding]:
    results = store.get_findings()
    if service:
        results = [f for f in results if f.service.lower() == service.lower()]
    if min_score is not None:
        results = [f for f in results if f.score >= min_score]
    if status:
        results = [f for f in results if (f.status or "open") == status]
    return results


def _filter_activity(store: Store, search: str | None = None, status: str | None = None) -> list[ActivityEvent]:
    events, _source = store.get_activity_log()
    results = list(events)
    if search:
        needle = search.lower()
        results = [e for e in results if needle in f"{e.actor} {e.action} {e.source} {e.system}".lower()]
    if status:
        results = [e for e in results if e.status == status]
    return results


def _filter_identities(store: Store, min_score: int | None = None) -> list[Identity]:
    results = store.get_identities()
    if min_score is not None:
        results = [i for i in results if i.score >= min_score]
    return results


_TOOL_IMPLEMENTATIONS = {
    "filter_findings": _filter_findings,
    "filter_activity": _filter_activity,
    "filter_identities": _filter_identities,
}


@router.post("/copilot/query", response_model=CopilotResponse)
def query_copilot(body: CopilotQueryRequest, store: Store = Depends(get_store)) -> CopilotResponse:
    messages: list[dict] = [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": body.question},
    ]

    try:
        message = call_chat_completions(messages, tools=_TOOLS)
        tool_calls = message.get("tool_calls") or []

        if not tool_calls:
            answer = (message.get("content") or "").strip() or _UNAVAILABLE_ANSWER
            return CopilotResponse(answer=answer, findings=[], activity=[], identities=[])

        findings: list[Finding] = []
        activity: list[ActivityEvent] = []
        identities: list[Identity] = []

        messages.append(message)
        for tool_call in tool_calls:
            function = tool_call["function"]
            name = function["name"]
            arguments = json.loads(function.get("arguments") or "{}")
            implementation = _TOOL_IMPLEMENTATIONS.get(name)
            if implementation is None:
                tool_result: list = []
            else:
                tool_result = implementation(store, **arguments)
                if name == "filter_findings":
                    findings = tool_result
                elif name == "filter_activity":
                    activity = tool_result
                elif name == "filter_identities":
                    identities = tool_result
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call["id"],
                    "content": json.dumps([item.model_dump() for item in tool_result]),
                }
            )

        # Bounded to one follow-up call: if this response also requests tool
        # calls, ignore them and use its text content as-is (research.md §5).
        follow_up = call_chat_completions(messages)
        answer = (follow_up.get("content") or "").strip() or _UNAVAILABLE_ANSWER

        return CopilotResponse(answer=answer, findings=findings, activity=activity, identities=identities)
    except AIServiceError:
        return CopilotResponse(answer=_UNAVAILABLE_ANSWER, findings=[], activity=[], identities=[])
