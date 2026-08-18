# Implementation Plan: AI-Assisted Investigation Features

**Branch**: `002-ai-features` | **Date**: 2026-08-18 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/002-ai-features/spec.md`

## Summary

Add three AI-backed capabilities to the Sentinel Access FastAPI backend: (1)
on-demand, per-finding plain-language explanations generated from a
finding's own evidence and cached in memory; (2) an "Ask Sentinel" natural-
language copilot endpoint that answers questions about findings/activity/
identities via bounded LLM tool-calling over the existing in-memory `Store`;
and (3) AI-generated narrative summaries for the "Prepare report" action,
regenerated fresh on every call. All three call a self-hosted liteLLM proxy
(OpenAI-compatible `/v1/chat/completions`, model alias
`genailab-maas-Opus-4.6`) over plain HTTP from the backend, with no new
database, no auth, and a documented in-line fallback whenever the proxy is
unreachable. Builds on the `Store`/routers/contracts already established by
001-fastapi-backend-migration.

## Technical Context

**Language/Version**: Python 3.11+ (same backend as 001); frontend stays TypeScript/React, unchanged in this plan beyond wiring three new fetches.

**Primary Dependencies**: FastAPI, Pydantic v2, `httpx` (already in `requirements.txt` — reused as the HTTP client to the liteLLM proxy; no new package required).

**Storage**: In-memory only — one new `Store` field (`finding_explanations: dict[str, str]`), per `data-model.md`. No database, no external cache.

**Testing**: `pytest` + FastAPI `TestClient`, mocking the liteLLM proxy HTTP call (e.g. via `respx` or a monkeypatched `httpx.Client`) so contract/integration tests don't depend on a live proxy; one test explicitly exercises the FR-007 fallback path by simulating a proxy failure.

**Target Platform**: Same local/dev Uvicorn process as 001 — this feature adds no new deployable backend component, but does introduce a dependency on an externally-run liteLLM proxy process (see Constitution Check below).

**Project Type**: Web application (existing frontend + existing FastAPI backend, extended).

**Performance Goals**: No hard SLA; LLM calls are inherently slower than the existing in-memory reads, so the frontend must show a loading state (FR-008) rather than target a specific latency. Informal target: proxy calls timeout client-side at 15s to keep the fallback path (FR-007) from hanging the UI indefinitely.

**Constraints**: No authentication/authorization on the new endpoints (constitution Principle III, matching 001). No new persistent datastore. Copilot tool-calling is read-only over existing `Store` data (spec Assumption) — it cannot start investigations, escalate, or otherwise mutate state. Must degrade gracefully (never 5xx) when the liteLLM proxy is unreachable (FR-007).

**Scale/Scope**: Same single-process, single-analyst demo scale as 001. The liteLLM proxy is assumed already running and configured by the operator (per `quickstart.md` Prerequisites) — provisioning/deploying the proxy itself is out of scope for this feature.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Check | Result |
|---|---|---|
| I. API-First Backend Migration | Each capability is a REST endpoint (`GET /api/findings/{id}/explanation`, `POST /api/copilot/query`, extended `POST /api/reports/{title}/prepare`) that the frontend consumes — no client-side-only AI logic. | PASS |
| II. Preserve Existing UX and Data Shapes | All three capabilities are additive fields/endpoints; no existing response field is renamed or removed (explanation endpoint is new/separate from `Finding`; report narrative adds one nullable field). | PASS |
| III. Simplicity and YAGNI (NON-NEGOTIABLE) | No database, no auth, no new persisted infra in the FastAPI backend itself. **One explicit, justified exception**: this feature depends on a separately-run liteLLM proxy process — see Complexity Tracking. | JUSTIFIED EXCEPTION (see below) |
| IV. Contract Clarity Before Implementation | Phase 1 produces `data-model.md` and `contracts/*.md` for all three capabilities before `/speckit-tasks` runs. | PASS |
| V. Demo-Safe Data Only | The LLM only ever sees data already present in the synthetic/demo `Store` (findings, activity, identities) — no new external or real data is introduced into prompts. | PASS |

**Post-Design Re-check** (after Phase 1 `data-model.md`/`contracts/`/`quickstart.md`):
the three new/extended contracts (`ai-explanations.md`, `ai-copilot.md`,
`ai-report-narrative.md`) confirm every AI-backed response has a
non-AI-dependent fallback path and none of them require a stored credential
beyond the three plain env vars (`LITELLM_PROXY_URL`, `LITELLM_API_KEY`,
`LITELLM_MODEL`) documented in `research.md` §3. Gates I, II, IV, V still
PASS; Gate III's justified exception is unchanged and fully scoped (below).

## Project Structure

### Documentation (this feature)

```text
specs/002-ai-features/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
│   ├── ai-explanations.md
│   ├── ai-copilot.md
│   └── ai-report-narrative.md
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
sentinel-access/
├── client/                          # EXISTING frontend
│   └── src/
│       ├── pages/Home.tsx           # evidence dossier: fetch explanation on open
│       ├── components/WorkspaceViews.tsx  # Reports view: render narrative
│       ├── components/CopilotPanel.tsx    # NEW: "Ask Sentinel" input + answer panel
│       └── lib/api.ts               # EXISTING — add getFindingExplanation / queryCopilot / (reuse prepareReport)
│
├── backend/                         # EXISTING FastAPI service (from 001)
│   ├── app/
│   │   ├── ai_client.py             # NEW: httpx wrapper around the liteLLM proxy chat-completions call
│   │   ├── store.py                 # extended: finding_explanations cache (data-model.md)
│   │   ├── schemas/entities.py      # extended: FindingExplanation, CopilotQuery/Response, narrative field
│   │   └── routers/
│   │       ├── command_center.py    # extended: GET /api/findings/{id}/explanation (FR-001/002)
│   │       ├── copilot.py           # NEW: POST /api/copilot/query (FR-003/004/005)
│   │       └── reports.py           # extended (built as part of 001 US3): narrative field on prepare (FR-006)
│   └── tests/
│       ├── contract/ai_explanations_test.py   # NEW
│       ├── contract/ai_copilot_test.py        # NEW
│       ├── contract/ai_report_narrative_test.py # NEW
│       └── integration/test_ai_fallback.py    # NEW — proxy-unreachable path (FR-007) across all three
│
└── server/                          # EXISTING Express static file server — unmodified
```

**Structure Decision**: Extend the existing `sentinel-access/backend/` FastAPI
service in place — no new backend project, no new frontend project. A single
new `ai_client.py` module centralizes the liteLLM proxy HTTP call (base URL,
auth header, timeout, error handling) so all three capabilities share one
tested code path rather than three ad-hoc `httpx` calls. The one new router
file is `copilot.py`; the explanation and report-narrative capabilities
extend the existing `command_center.py` and `reports.py` routers (the latter
being built as part of 001's still-pending User Story 3) rather than adding
new router files, since they're additive to endpoints those routers already
own.

## Complexity Tracking

> Constitution Principle III ("no external services... not required by the
> current demo scope") is a NON-NEGOTIABLE gate, so this deviation is
> recorded explicitly rather than waved through.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|---|---|---|
| Dependency on an externally-run liteLLM proxy process (a component beyond the FastAPI backend + Vite frontend + Express static server already in the project) | The feature's entire purpose is calling a real LLM; the user has explicitly chosen a liteLLM proxy (already running, OpenAI-compatible, confirmed working) as the integration layer over the alternative of an in-process SDK call, specifically so the AI provider stays swappable without backend code changes. | An in-process `litellm` Python SDK call (no separate process) was considered and rejected in `research.md` §1 — the user is already operating a proxy and wants the backend to call it, not duplicate its routing/config in-process. A raw direct-to-Anthropic SDK call was also rejected earlier in this feature's design (see spec conversation) in favor of the provider-swappable proxy the user is running. |

**Sign-off**: Confirmed accepted by the project owner on 2026-08-18 as a scoped, one-feature exception — not a general relaxation of Principle III.
