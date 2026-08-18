---

description: "Task list template for feature implementation"
---

# Tasks: AI-Assisted Investigation Features

**Input**: Design documents from `/specs/002-ai-features/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Not explicitly requested in the spec; a light contract/integration test pass is
included in the Polish phase only (matching the pattern already established in
`specs/001-fastapi-backend-migration/tasks.md`), not as a per-story TDD gate.

**Organization**: Tasks are grouped by user story (from `spec.md`) to enable independent
implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- File paths are relative to the repository root (`sentinel-access/` is the existing project)

## Path Conventions

Per `plan.md`'s Structure Decision — this feature extends the existing 001 backend/frontend
in place, no new projects:
- Backend (existing, extended): `sentinel-access/backend/app/`
- Frontend (existing, extended): `sentinel-access/client/src/`

---

## Phase 1: Setup

**Purpose**: Document the new configuration surface before any code depends on it.

- [X] T001 Document `LITELLM_PROXY_URL` (default `http://localhost:4000`), `LITELLM_API_KEY` (required), and `LITELLM_MODEL` (default `genailab-maas-Opus-4.6`) in `sentinel-access/backend/.env.example` (create the file if it doesn't exist) per `research.md` §3. No new Python dependency is needed — `httpx` is already in `requirements.txt`.

**Checkpoint**: Configuration surface documented; no new dependencies to install.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The single shared LLM transport that every AI capability calls through.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T002 Create `sentinel-access/backend/app/ai_client.py`: reads `LITELLM_PROXY_URL`/`LITELLM_API_KEY`/`LITELLM_MODEL` from env at import time; exposes `call_chat_completions(messages: list[dict], tools: list[dict] | None = None) -> dict` that `POST`s to `{LITELLM_PROXY_URL}/v1/chat/completions` with `Authorization: Bearer {LITELLM_API_KEY}`, `model={LITELLM_MODEL}`, and a 15s timeout using a sync `httpx.Client`; raises a module-level `AIServiceError` on network errors, non-2xx responses, or a missing/empty `choices` in the response body, per `research.md` §1-§4 and §7.

**Checkpoint**: `ai_client.call_chat_completions` ready — user story phases can now begin.

---

## Phase 3: User Story 1 - AI-generated finding explanations (Priority: P1) 🎯 MVP

**Goal**: Evidence dossiers show a plain-language explanation generated from each finding's own evidence, cached after first generation.

**Independent Test**: Open several different findings' evidence dossiers and confirm each shows a distinct, evidence-specific explanation; reopen the same finding and confirm the same text is served without a new generation delay (per `quickstart.md` Step 2).

### Implementation for User Story 1

- [X] T003 [P] [US1] Add `FindingExplanation` schema (`findingId: str`, `explanation: str`, `source: Literal["ai","fallback"]`) to `sentinel-access/backend/app/schemas/entities.py` per `data-model.md`.
- [X] T004 [P] [US1] Extend `Store` in `sentinel-access/backend/app/store.py`: add `finding_explanations: dict[str, str]`, `get_finding_explanation(finding_id) -> str | None`, and `cache_finding_explanation(finding_id, text) -> None`.
- [X] T005 [US1] Implement `GET /api/findings/{finding_id}/explanation` in `sentinel-access/backend/app/routers/command_center.py`: on cache hit return it with `source: "ai"`; on cache miss, build a prompt from the finding's `signals`/`baseline`/`description`, call `ai_client.call_chat_completions`, cache and return the result with `source: "ai"`; on `AIServiceError`, return the finding's existing `description`/`baseline` text with `source: "fallback"` (uncached — retry AI on the next request) per `contracts/ai-explanations.md`. 404 on unknown `finding_id` (depends on T002, T003, T004).
- [X] T006 [US1] In `sentinel-access/client/src/lib/api.ts`, add `getFindingExplanation(findingId: string)` calling `GET /api/findings/{id}/explanation`.
- [X] T007 [US1] In `sentinel-access/client/src/pages/Home.tsx`, fetch the AI explanation when the evidence dossier opens (loading state while pending, per FR-008) and render it in the dossier in place of the static explanation text.

**Checkpoint**: User Story 1 is fully functional and independently demoable (MVP).

---

## Phase 4: User Story 2 - "Ask Sentinel" natural-language copilot (Priority: P1)

**Goal**: An analyst can ask a plain-English question and get an answer backed by real matching findings/activity/identities.

**Independent Test**: Ask several natural-language questions covering findings, activity, and identities and confirm each returns a relevant answer plus the correct matching records; ask an out-of-scope or no-match question and confirm a graceful, non-fabricated response (per `quickstart.md` Step 3).

### Implementation for User Story 2

- [X] T008 [P] [US2] Add `CopilotQueryRequest` (`question: str`) and `CopilotResponse` (`answer: str`, `findings: list[Finding]`, `activity: list[ActivityEvent]`, `identities: list[Identity]`) schemas to `sentinel-access/backend/app/schemas/entities.py` per `data-model.md`.
- [X] T009 [P] [US2] Create `sentinel-access/backend/app/routers/copilot.py` with three read-only tool implementations backed by the `Store` — `filter_findings(service?, min_score?, status?)`, `filter_activity(search?, status?)`, `filter_identities(min_score?)` — and their OpenAI-style tool-call JSON schema definitions, per `research.md` §5.
- [X] T010 [US2] Implement `POST /api/copilot/query` in `copilot.py`: send the question + tool definitions to `ai_client.call_chat_completions`; if the response includes `tool_calls`, execute the matching `Store` read(s) locally and make one follow-up call with the results appended as `tool` messages, then return the model's final text as `answer` plus whichever result list(s) were populated — if that follow-up response *also* contains `tool_calls` (the loop is capped at one round-trip), ignore them and use its text content as-is rather than making a third call; if no tool call was made on the first response, return the model's text directly (handles out-of-scope/no-match per FR-005); on `AIServiceError`, return HTTP 200 with an "AI assistant is unavailable" `answer` and empty result lists per `contracts/ai-copilot.md` (depends on T002, T008, T009).
- [X] T011 [US2] Register the copilot router in `sentinel-access/backend/app/main.py`.
- [X] T012 [US2] In `sentinel-access/client/src/lib/api.ts`, add `queryCopilot(question: string)` calling `POST /api/copilot/query`.
- [X] T013 [US2] Create `sentinel-access/client/src/components/CopilotPanel.tsx`: an "Ask Sentinel" text input, submit action, and an answer display listing any matched findings/activity/identities, with a loading state while the query is in flight (FR-008).
- [X] T014 [US2] Wire `CopilotPanel` into `sentinel-access/client/src/pages/Home.tsx` (e.g. a panel reachable from the Command Center) so analysts can open and use it.

**Checkpoint**: User Stories 1 and 2 both independently functional.

---

## Phase 5: User Story 3 - AI-drafted report narratives (Priority: P2)

**Goal**: "Prepare report" returns a generated narrative reflecting current findings/activity, alongside the existing completion confirmation.

**Independent Test**: Prepare each report template and confirm the narrative reflects current data; simulate a new finding and prepare the same template again, confirming the narrative changes (per `quickstart.md` Step 4).

### Implementation for User Story 3

- [X] T015 [US3] Check `specs/001-fastapi-backend-migration/tasks.md` T027/T028 status: if both are already checked off, confirm `sentinel-access/backend/app/routers/reports.py` exists and matches `specs/001-fastapi-backend-migration/contracts/reports.md`, then skip to T016. (Confirmed: both endpoints already implemented and registered.)
- [X] ~~T015a~~ [US3] Not needed — base endpoint already existed.
- [X] T016 [US3] Extend the report-prepare response schema in `sentinel-access/backend/app/schemas/entities.py` with `narrative: str | None` per `contracts/ai-report-narrative.md`.
- [X] T017 [US3] In `reports.py`'s prepare handler, call `ai_client.call_chat_completions` with a prompt built from current `store.findings`/`store.activity_log` to generate `narrative` fresh on every call (not cached, per `data-model.md`); on `AIServiceError`, set `narrative: None` while still returning the existing `status`/`preparedAt` fields successfully (depends on T002, T015, T016).
- [X] T017a [US3] In `sentinel-access/client/src/components/WorkspaceViews.tsx`'s "Prepare report" action, show a loading state while the request is in flight, per FR-008 (matching the pattern used in T007/T013 for the other two AI actions).
- [X] T018 [US3] In `sentinel-access/client/src/components/WorkspaceViews.tsx`, render the returned `narrative` in the Reports view's prepared-report confirmation (toast/detail panel), handling `narrative: null` gracefully.

**Checkpoint**: All three user stories independently functional.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Resilience, test coverage, and final verification across all three AI capabilities.

- [X] T019 [P] Confirm consistent loading/error UI treatment across the evidence dossier explanation, `CopilotPanel`, and the report-prepare narrative (FR-008, SC-004) — no AI-backed action should leave the UI in an ambiguous state.
- [X] T020 [P] Write contract tests in `sentinel-access/backend/tests/contract/` for `ai-explanations`, `ai-copilot`, and `ai-report-narrative` (one module each), mocking `ai_client.call_chat_completions` so tests don't depend on a live proxy, per `plan.md`'s Testing section.
- [X] T021 Write `sentinel-access/backend/tests/integration/test_ai_fallback.py`: simulate `ai_client.call_chat_completions` raising `AIServiceError` and assert all three endpoints degrade per FR-007 — 200 responses with the documented fallback content, never a 5xx.
- [X] T022 Run `quickstart.md` steps 1-5 end-to-end. Verified without a live liteLLM proxy configured (no `LITELLM_API_KEY` in this environment): `GET /api/findings/{id}/explanation`, `POST /api/copilot/query`, and `POST /api/reports/{title}/prepare` were exercised live via curl against a running backend and all three correctly hit the FR-007 fallback path (Step 5) — explanation returns `source: "fallback"` with the finding's description/baseline text, copilot returns the unavailable message with empty arrays, and report prepare still returns `status: "ready"` with `narrative: null`. Steps 2-4 (AI-generated content, SC-001/002/003/005) require a live liteLLM proxy to verify and were not re-run here — the full `pytest` suite (36/36 passing, including new contract/integration tests) covers the AI-generated-content code paths with a mocked proxy instead.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately.
- **Foundational (Phase 2)**: Depends on Setup — BLOCKS all user stories.
- **User Story 1 (Phase 3)**: Depends on Foundational only. This is the MVP.
- **User Story 2 (Phase 4)**: Depends on Foundational only; independent of US1 (different router/component), can run in parallel with US1 if staffed.
- **User Story 3 (Phase 5)**: Depends on Foundational (T002) and on the base reports endpoint existing (T015, which itself completes outstanding work from the 001 feature) — implement after US1/US2, or in parallel if T015's prerequisite is already satisfied.
- **Polish (Phase 6)**: Depends on all three user stories being complete.

### Within Each User Story

- Schema/model tasks before the endpoint task that uses them.
- Router implementation before frontend wiring tasks that call it.

### Parallel Opportunities

- T003/T004 (US1 schema + store) can run in parallel.
- T008/T009 (US2 schema + tool implementations) can run in parallel.
- US1 (Phase 3) and US2 (Phase 4) can be built in parallel once Phase 2 is done, since they touch different router/component files.
- T019/T020 in Polish can run in parallel.

---

## Parallel Example: User Story 1

```bash
# Launch US1's independent-file tasks together:
Task: "Add FindingExplanation schema in sentinel-access/backend/app/schemas/entities.py"
Task: "Extend Store with finding_explanations cache in sentinel-access/backend/app/store.py"

# Then, once both are done:
Task: "Implement GET /api/findings/{finding_id}/explanation in sentinel-access/backend/app/routers/command_center.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (blocks everything)
3. Complete Phase 3: User Story 1 (finding explanations)
4. **STOP and VALIDATE**: run `quickstart.md` steps 1-2; confirm SC-001 and SC-002
5. Demo AI-generated finding explanations as the MVP

### Incremental Delivery

1. Setup + Foundational → shared `ai_client` ready
2. User Story 1 → validate independently → MVP demoable
3. User Story 2 → validate independently → Ask Sentinel copilot live
4. User Story 3 → validate independently → AI report narratives live
5. Polish → fallback test coverage, full quickstart pass (SC-001 through SC-005)

Each story adds value without breaking previously delivered stories, since each owns
distinct router/component files and shares only the read-only `ai_client` transport.
