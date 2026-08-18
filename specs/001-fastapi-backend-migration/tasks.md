---
description: "Task list template for feature implementation"
---

# Tasks: FastAPI Backend Migration

**Input**: Design documents from `/specs/001-fastapi-backend-migration/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Not explicitly requested in the spec; a light contract/integration test pass is
included in the Polish phase only (matching the `backend/tests/` layout already decided
in `plan.md`), not as a per-story TDD gate.

**Organization**: Tasks are grouped by user story (from `spec.md`) to enable independent
implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3, US4)
- File paths are relative to the repository root (`sentinel-access/` is the existing project)

## Path Conventions

Per `plan.md`'s Structure Decision:
- Backend (new): `sentinel-access/backend/app/`, `sentinel-access/backend/tests/`
- Frontend (existing, modified in place): `sentinel-access/client/src/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Stand up the new backend project and the dev connection to the frontend.

- [X] T001 Create `sentinel-access/backend/` structure: `app/`, `app/schemas/`, `app/routers/`, `tests/contract/`, `tests/integration/` (empty `__init__.py` files as needed), per `plan.md` Project Structure.
- [X] T002 Create `sentinel-access/backend/requirements.txt` with `fastapi`, `uvicorn`, `pydantic`, `python-multipart`, `pytest`, `httpx` (per `research.md` §5 and `plan.md` Technical Context).
- [X] T003 [P] Add a `server.proxy` entry for `/api` → `http://localhost:8001` in `sentinel-access/vite.config.ts` (per `research.md` §3).
- [X] T004 [P] Create `sentinel-access/client/src/lib/api.ts`: an axios instance with `baseURL: "/api"` for all backend calls.

**Checkpoint**: Backend project scaffolded; frontend can reach `/api/*` in dev.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core data layer and app skeleton that every user story's endpoints depend on.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T005 Create `sentinel-access/backend/app/schemas/entities.py` with Pydantic models for every entity in `data-model.md`: `Finding`, `SummaryMetrics`, `ModelRationale`, `AccessTrendPoint`, `ServiceRisk`, `ServiceRiskSummary`, `ActivityEvent`, `Identity`, `CloudSource`, `PolicyRule`, `ReportTemplate`, `Configuration`, `DatasetImportResult`.
- [X] T006 Create `sentinel-access/backend/app/seed_data.py`: loads `sentinel-access/server/data/synthetic-data.json` at import time and converts each section into the Phase-T005 Pydantic models.
- [X] T007 Create `sentinel-access/backend/app/store.py`: an in-memory `Store` class (per `data-model.md` "Store shape") constructed once from `seed_data.py`, exposing methods used by routers (`get_findings`, `get_finding(id)`, `update_finding_status(id, status)`, `add_finding(finding)`, `compute_summary_metrics()`, `get_activity_log()`, `replace_activity_log(events, source)`, `get_identities()`, `get_cloud_sources()`, `get_policies()`, `toggle_policy(title)`, `get_reports()`, `get_configuration()`, `set_configuration(config)`).
- [X] T008 Create `sentinel-access/backend/app/main.py`: FastAPI app instance, permissive CORS middleware (per `research.md` §3), a single shared `Store` instance provided via FastAPI dependency injection, and router registration (routers added in later phases).
- [X] T009 [P] Add a startup log line in `sentinel-access/backend/app/main.py` printing seeded counts (findings/identities/policies) for quickstart verification (`quickstart.md` step 1).

**Checkpoint**: Foundation ready — user story phases can now begin.

---

## Phase 3: User Story 1 - Command Center runs on live data (Priority: P1) 🎯 MVP

**Goal**: Command Center (KPIs, queue, charts, evidence dossier) is served by the backend;
start investigation / escalate / simulate anomaly are backend-persisted actions.

**Independent Test**: Load the Command Center, compare rendered values against
`GET /api/command-center`; click "Start investigation," reload the page, confirm the
status change survived (per `quickstart.md` steps 3-4).

### Implementation for User Story 1

- [X] T010 [P] [US1] Implement `GET /api/command-center` in `sentinel-access/backend/app/routers/command_center.py` per `contracts/command-center.md` (computes `summaryMetrics` via `store.compute_summary_metrics()`).
- [X] T011 [P] [US1] Implement `GET /api/findings/{finding_id}` (404 on unknown id) in `sentinel-access/backend/app/routers/command_center.py` per `contracts/command-center.md`.
- [X] T012 [US1] Implement `POST /api/findings/{finding_id}/status` (validates `status` enum, 404 on unknown id) in `sentinel-access/backend/app/routers/command_center.py` (depends on T007, T011).
- [X] T013 [US1] Implement `POST /api/findings/simulate-anomaly` (creates and returns a new synthetic `Finding`) in `sentinel-access/backend/app/routers/command_center.py` (depends on T007).
- [X] T014 [US1] Register the command-center router in `sentinel-access/backend/app/main.py` (depends on T010-T013).
- [X] T015 [US1] In `sentinel-access/client/src/pages/Home.tsx`, replace the hardcoded KPI/queue/chart constants with a `GET /api/command-center` fetch on mount, using `api.ts` (T004).
- [X] T016 [US1] In `sentinel-access/client/src/pages/Home.tsx`, fetch `GET /api/findings/{id}` when the evidence dossier opens instead of reading from local state.
- [X] T017 [US1] In `sentinel-access/client/src/pages/Home.tsx`, wire "Start investigation" to `POST /api/findings/{id}/status` with `{ "status": "in_progress" }`, closing the dossier and refreshing the queue on success.
- [X] T018 [US1] In `sentinel-access/client/src/pages/Home.tsx`, wire "Escalate" to `POST /api/findings/{id}/status` with `{ "status": "escalated" }`.
- [X] T019 [US1] In `sentinel-access/client/src/pages/Home.tsx`, wire the "Simulate anomaly" button to `POST /api/findings/simulate-anomaly` and prepend the returned finding to the visible queue.

**Checkpoint**: Command Center is fully backend-driven and independently testable/demoable (MVP).

---

## Phase 4: User Story 2 - Explorer, Identity, and Estate views run on live data (Priority: P2)

**Goal**: Activity Explorer, Identity Profiles, and Cloud Estate read from the backend.

**Independent Test**: Load each of the three views and compare rendered content against
`GET /api/activity`, `GET /api/identities`, and `GET /api/estate` respectively
(per `quickstart.md` step 3).

### Implementation for User Story 2

- [X] T020 [P] [US2] Implement `GET /api/activity` (with optional `search`/`status` query params) in `sentinel-access/backend/app/routers/activity.py` per `contracts/activity.md`.
- [X] T021 [P] [US2] Implement `GET /api/identities` and `GET /api/identities/{name}/timeline` (404 on unknown name) in `sentinel-access/backend/app/routers/identities.py` per `contracts/identities.md`.
- [X] T022 [P] [US2] Implement `GET /api/estate` in `sentinel-access/backend/app/routers/estate.py` per `contracts/estate.md`.
- [X] T023 [US2] Register the activity, identities, and estate routers in `sentinel-access/backend/app/main.py` (depends on T020-T022).
- [X] T024 [P] [US2] In `sentinel-access/client/src/components/WorkspaceViews.tsx`, replace Activity Explorer's hardcoded event list with a `GET /api/activity` fetch, passing the UI's existing search/status filter state as query params.
- [X] T025 [P] [US2] In `sentinel-access/client/src/components/WorkspaceViews.tsx`, replace Identity Profiles' hardcoded card data with `GET /api/identities`, and fetch `GET /api/identities/{name}/timeline` when a profile is opened.
- [X] T026 [P] [US2] In `sentinel-access/client/src/components/WorkspaceViews.tsx`, replace Cloud Estate's hardcoded source list with a `GET /api/estate` fetch.

**Checkpoint**: All read-heavy investigation views are backend-driven, independent of US1's write actions.

---

## Phase 5: User Story 3 - Policies, Reports, and Configuration act through the backend (Priority: P3)

**Goal**: Policy toggles, report preparation, and settings saves are persisted server-side.

**Independent Test**: Toggle a policy, prepare a report, save a setting; reload and confirm
each change persisted via the backend (per `quickstart.md`, extending step 3's pattern).

### Implementation for User Story 3

- [X] T027 [P] [US3] Implement `GET /api/policies` and `POST /api/policies/{title}/toggle` (404 on unknown title) in `sentinel-access/backend/app/routers/policies.py` per `contracts/policies.md`.
- [X] T028 [P] [US3] Implement `GET /api/reports`, `POST /api/reports/{title}/prepare`, and `GET /api/reports/export.csv` in `sentinel-access/backend/app/routers/reports.py` per `contracts/reports.md`.
- [X] T029 [P] [US3] Implement `GET /api/configuration` and `PUT /api/configuration` in `sentinel-access/backend/app/routers/configuration.py` per `contracts/configuration.md`.
- [X] T030 [US3] Register the policies, reports, and configuration routers in `sentinel-access/backend/app/main.py` (depends on T027-T029).
- [X] T031 [P] [US3] In `sentinel-access/client/src/components/WorkspaceViews.tsx`, wire the Policies view's toggle control to `POST /api/policies/{title}/toggle`.
- [X] T032 [P] [US3] In `sentinel-access/client/src/components/WorkspaceViews.tsx`, wire "Prepare report" to `POST /api/reports/{title}/prepare` and the global "Export activity CSV" action to `GET /api/reports/export.csv`.
- [X] T033 [P] [US3] In `sentinel-access/client/src/components/WorkspaceViews.tsx`, wire the Configuration view to load via `GET /api/configuration` and "Save preferences" to `PUT /api/configuration`.

**Checkpoint**: Administrative views are backend-driven.

---

## Phase 6: User Story 4 - Dataset import is handled by the backend (Priority: P3)

**Goal**: CSV/JSON dataset uploads are validated and ingested server-side, replacing the
active `activity_log`, instead of being parsed entirely in-browser.

**Independent Test**: Upload a valid CSV and confirm Activity Explorer reflects the imported
records with `"source": "imported"`; upload an invalid file and confirm a clear error with
no data corruption (per `quickstart.md` step 5).

### Implementation for User Story 4

- [X] T034 [US4] Implement `POST /api/datasets` in `sentinel-access/backend/app/routers/datasets.py` per `contracts/datasets.md`: parse CSV (stdlib `csv`) or JSON, validate required `ActivityEvent` fields and the 10,000-record cap, call `store.replace_activity_log(...)` on success, and return `DatasetImportResult` (depends on T007, T020).
- [X] T035 [US4] Register the datasets router in `sentinel-access/backend/app/main.py` (depends on T034).
- [X] T036 [US4] In `sentinel-access/client/src/components/DatasetImporter.tsx`, replace the in-browser CSV/JSON parsing with a `multipart/form-data` upload to `POST /api/datasets`.
- [X] T037 [US4] In `sentinel-access/client/src/components/DatasetImporter.tsx`, display the backend's `acceptedCount`/`rejectedCount`/`errors` summary (replacing the old client-computed summary).
- [X] T038 [US4] Confirm `sentinel-access/client/src/components/WorkspaceViews.tsx`'s Activity Explorer (T024) surfaces the `"source": "imported"` flag from `GET /api/activity` so the existing "imported vs. synthetic" data-lifecycle messaging still works.

**Checkpoint**: All four user stories are independently functional; hardcoded fixtures are fully superseded.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Resilience, cleanup, and final verification across all stories.

- [X] T039 [P] Add a shared loading/error UI state in `sentinel-access/client/src/pages/Home.tsx` and `sentinel-access/client/src/components/WorkspaceViews.tsx` for failed/unreachable backend requests (SC-004).
- [X] T040 [P] Write contract tests (one module per router, asserting response shape/status codes) in `sentinel-access/backend/tests/contract/` for all routers from Phases 3-6.
- [X] T041 [P] Write an integration test in `sentinel-access/backend/tests/integration/test_finding_status.py`: start an investigation via `POST`, then `GET` the finding again and assert the status persisted (SC-002).
- [X] T042 Remove the now-unused hardcoded fixture constants from `sentinel-access/client/src/pages/Home.tsx` and `sentinel-access/client/src/components/WorkspaceViews.tsx` once all views read from the backend.
- [X] T043 Run through `quickstart.md` end-to-end (steps 1-7) and confirm SC-001 through SC-005 all hold.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately.
- **Foundational (Phase 2)**: Depends on Setup — BLOCKS all user stories.
- **User Story 1 (Phase 3)**: Depends on Foundational only. This is the MVP.
- **User Story 2 (Phase 4)**: Depends on Foundational only; independent of US1 (different routers/views), can run in parallel with US1 if staffed.
- **User Story 3 (Phase 5)**: Depends on Foundational only; independent of US1/US2.
- **User Story 4 (Phase 6)**: Depends on Foundational (T007) and on US2's `activity.py` router existing (T020), since dataset import replaces the same `activity_log` that `GET /api/activity` reads — implement after Phase 4.
- **Polish (Phase 7)**: Depends on all four user stories being complete.

### Within Each User Story

- Backend router implementation before router registration in `main.py`.
- Router registration before the corresponding frontend fetch-wiring tasks (frontend needs a live endpoint to call against, even if a mock/manual `curl` check is used first).

### Parallel Opportunities

- T003/T004 (Setup) can run in parallel.
- T005-T009 (Foundational) are mostly sequential (T006 needs T005, T007 needs T006, T008 needs T007); T009 can run in parallel with T008 once T007 is done.
- US1, US2, and US3 backend router tasks (T010-T013, T020-T022, T027-T029) can all run in parallel across stories once Foundational is done, since each touches a different router file.
- Within US2 and US3, the three router-implementation tasks and the three frontend-wiring tasks are each mutually parallel ([P]-marked).
- T039-T041 in Polish can run in parallel.

---

## Parallel Example: User Story 2

```bash
# Launch all three router implementations for User Story 2 together:
Task: "Implement GET /api/activity in sentinel-access/backend/app/routers/activity.py"
Task: "Implement GET /api/identities and timeline in sentinel-access/backend/app/routers/identities.py"
Task: "Implement GET /api/estate in sentinel-access/backend/app/routers/estate.py"

# After registration (T023), launch all three frontend-wiring tasks together:
Task: "Wire Activity Explorer to GET /api/activity in WorkspaceViews.tsx"
Task: "Wire Identity Profiles to GET /api/identities in WorkspaceViews.tsx"
Task: "Wire Cloud Estate to GET /api/estate in WorkspaceViews.tsx"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (blocks everything)
3. Complete Phase 3: User Story 1 (Command Center)
4. **STOP and VALIDATE**: run `quickstart.md` steps 1-4; confirm SC-001 (Command Center) and SC-002
5. Demo the live Command Center as the MVP

### Incremental Delivery

1. Setup + Foundational → foundation ready
2. User Story 1 → validate independently → MVP demoable
3. User Story 2 → validate independently → Explorer/Identity/Estate live
4. User Story 3 → validate independently → Policies/Reports/Configuration live
5. User Story 4 → validate independently → dataset import fully backend-driven
6. Polish → cleanup, resilience, full quickstart pass (SC-001 through SC-005)

Each story adds value without breaking previously delivered stories, since each owns
distinct router files and distinct sections of `Home.tsx`/`WorkspaceViews.tsx`.
