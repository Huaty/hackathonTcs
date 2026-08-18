# Phase 0 Research: AI-Assisted Investigation Features

## 1. LLM transport: liteLLM proxy over HTTP vs. liteLLM SDK in-process

**Decision**: Backend calls a self-hosted liteLLM proxy's OpenAI-compatible
`POST /v1/chat/completions` endpoint over plain HTTP, using the `httpx`
client already in `requirements.txt` (no new dependency).

**Rationale**: Confirmed by the user with a working example — the proxy is
already running (observed response carries `"model":"genailab-maas-Opus-4.6"`,
an internal alias for Claude Opus 4.6) and reachable at an OpenAI-compatible
endpoint with a bearer virtual key. Calling it over HTTP keeps the backend
provider-agnostic (swap the proxy's upstream without touching backend code)
and avoids adding the `litellm` Python package (and its own dependency tree)
to a FastAPI service that already has an HTTP client available.

**Alternatives considered**: `litellm` Python SDK in-process (`litellm.completion(...)`)
— rejected because the user is already running a proxy server and wants the
backend to call it, not duplicate that routing logic in-process.

## 2. Sync vs. async request handling

**Decision**: New AI-backed routes stay `def` (sync), matching every existing
router in the codebase (`command_center.py`, `activity.py`, etc.), and use a
sync `httpx.Client` for the proxy call. FastAPI runs sync route handlers in a
threadpool, so a blocking HTTP call here does not block the event loop.

**Rationale**: Consistency with the existing codebase (constitution Principle
II's spirit — don't introduce a second style) outweighs the marginal
throughput benefit of async for a single-analyst demo tool with no
concurrency requirement (spec Scale/Scope: single-process demo).

**Alternatives considered**: `async def` + `httpx.AsyncClient` — rejected as
unnecessary complexity for this scale, and it would be the only async code
path in the backend.

## 3. Configuration surface

**Decision**: Three new environment variables, read once at startup into a
small `AIConfig` object (mirrors how `seed_data.py` loads its JSON once):

| Env var | Purpose | Default |
|---|---|---|
| `LITELLM_PROXY_URL` | Base URL of the liteLLM proxy | `http://localhost:4000` |
| `LITELLM_API_KEY` | Bearer virtual key sent as `Authorization` | *(required, no default)* |
| `LITELLM_MODEL` | Model alias to request | `genailab-maas-Opus-4.6` |

**Rationale**: Matches the project's existing no-new-infra posture (Principle
III) — this is the same "configuration, not infrastructure" pattern as the
current `vite.config.ts` API proxy. No secrets file, no vault; the proxy
itself already holds the real upstream Anthropic credentials.

## 4. Request/response shape against the proxy

**Decision**: Requests use the OpenAI chat-completions shape:
`{"model": <LITELLM_MODEL>, "messages": [...], "tools": [...]?}`. Responses
are parsed via `response["choices"][0]["message"]["content"]` (and
`["message"]["tool_calls"]` for the copilot's tool-calling flow), matching
the confirmed sample response's `object: "chat.completion"` shape. Fields
specific to the proxy (`usage.cache_read_input_tokens`, `inference_geo`,
`service_tier`, etc.) are read for nothing beyond optional debug logging —
the backend does not depend on them.

**Rationale**: This is the literal shape the user's proxy already returns;
no translation layer needed.

## 5. Tool-calling pattern for the copilot

**Decision**: A single bounded request/response-with-tools loop (max 2 model
calls per query), using OpenAI-style function tool definitions:
`filter_findings(service?, min_score?, status?)`,
`filter_activity(search?, status?)`, `filter_identities(min_score?)`. Each
tool's implementation is a pure read over the existing `Store` — no new data
source, no write capability (per spec Assumption: copilot is read-only).

Flow: (1) send the analyst's question + tool definitions; (2) if the model
returns `tool_calls`, execute the matching `Store` read(s) locally, prompt
the model again with the results appended as `tool` role messages, and take
its final text as the answer; (3) if the model's first response already has
no tool call (e.g., an out-of-scope or unanswerable question), use that text
directly as the decline/answer. This satisfies FR-004/FR-005 (only real data
surfaced, graceful decline) without an open-ended agent loop.

**Rationale**: The in-memory dataset is small and fully enumerable, so a
single tool round-trip is sufficient — no need for the multi-turn Tool
Runner or Managed Agents machinery documented for larger, more open-ended
agentic tasks. Bounding to one tool round-trip also keeps latency and cost
predictable for a demo.

**Alternatives considered**: Unbounded agentic loop — rejected as
unnecessary for a small, fully in-memory dataset and adds failure surface
(a runaway loop) with no corresponding benefit here.

## 6. Caching finding explanations

**Decision**: Add `finding_explanations: dict[str, str]` to the in-memory
`Store` (keyed by `Finding.id`), populated lazily on first request per
finding (FR-002). No TTL/invalidation logic — per spec Edge Cases, staleness
after a status change is explicitly accepted, and the store already resets
wholesale on backend restart (constitution Principle III / 001 spec
Assumptions).

**Rationale**: Simplest mechanism that satisfies FR-002's "don't regenerate
on repeat views" requirement; consistent with how `Store` already caches
computed-but-stable state (e.g., `model_rationale`).

## 7. Fallback behavior on AI failure (FR-007)

**Decision**: Each AI-backed endpoint wraps its proxy call in a
try/except around network errors, non-2xx responses, and response-shape
mismatches (missing/empty `choices`), and returns a clear fallback rather
than propagating a 500:

- **Finding explanation**: falls back to the finding's existing
  `description`/`baseline` text (already present in `data-model.md`'s
  `Finding`) with a response flag `source: "fallback"` instead of `"ai"`.
- **Copilot**: returns HTTP 200 with `answer` set to a clear "AI assistant is
  unavailable right now" message and empty result arrays — not a 5xx, so the
  frontend can render it as a normal (if disappointing) chat turn rather
  than an error boundary.
- **Report prepare**: the existing non-AI "prepared" confirmation
  (`status: "ready"`, `preparedAt`) still returns successfully; `narrative`
  is simply omitted (`null`) rather than blocking the whole action.

**Rationale**: Directly satisfies FR-007 and SC-004 ("every AI-backed action
still leaves the analyst with a usable, non-broken experience"). Keeping the
non-AI parts of each response successful (200) even when the AI call fails
avoids conflating "AI degraded" with "request failed."

## Technical Context resolution

All "NEEDS CLARIFICATION" placeholders in the plan template are resolved
using the decisions above; no unknowns remain.
