---
description: "Task list template for feature implementation"
---

# Tasks: SQLite In-Memory Storage & Additive Dataset Uploads

**Input**: Design documents from `/specs/003-sqlite-storage/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Not explicitly requested as TDD in the spec; following `001-fastapi-backend-migration`'s
established convention, tests are written alongside/after each story's implementation
(contract tests updated where behavior changed, new integration tests added for the
new accumulation/live-KPI behavior), not as a per-story TDD gate.

**Organization**: Tasks are grouped by user story (from `spec.md`) to enable independent
implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- File paths are relative to the repository root (`sentinel-access/` is the existing project)

## Path Conventions

Per `plan.md`'s Structure Decision — this feature modifies the existing
`sentinel-access/backend/` FastAPI service in place; no new project/service:
- `sentinel-access/backend/app/db.py` (new)
- `sentinel-access/backend/app/seed_data.py`, `app/store.py` (rewritten internals, same public shape)
- `sentinel-access/backend/app/routers/datasets.py` (one call-site change)
- `sentinel-access/backend/tests/contract/`, `tests/integration/` (existing + new)

**Important compatibility constraint** (found by inspecting current router
code, not just `data-model.md`): several routers read `Store` **attributes**
directly, not just methods —
`command_center.py` reads `store.model_rationale`, `store.access_trend`,
`store.access_trend_peak_label`, `store.service_risk`,
`store.service_risk_summary`; `main.py`'s startup log reads
`store.findings`, `store.identities`, `store.policies` as list-like
attributes (for `len(...)`). The SQLite rewrite MUST keep these working as
plain attribute access (e.g. via `@property` on `Store` that queries SQLite
on access) — every task below that touches `store.py` must preserve this,
since these call sites are out of scope to modify (per plan.md: "every
router... is unaffected at the call-site level").

---

## Phase 1: Setup

**Purpose**: Confirm there's no new dependency/config work needed before touching storage internals.

- [X] T001 Confirm `sentinel-access/backend/requirements.txt` needs no changes (Python's `sqlite3` is standard library — per `research.md` §1); add a one-line comment near the top noting SQLite storage uses the stdlib, no new package required.

**Checkpoint**: No new dependencies; ready to build the storage layer.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Stand up the SQLite-backed storage layer that every user story depends on. No story is testable until this phase is done.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T002 Create `sentinel-access/backend/app/db.py`: a module-level `sqlite3.connect(":memory:", check_same_thread=False)` connection singleton, an `init_schema(conn)` function creating every table listed in `data-model.md`'s "SQLite schema" section (`findings`, `activity_log`, `identities`, `cloud_sources`, `policies`, `reports`, `access_trend`, `service_risk`, `finding_explanations`, `model_rationale`, `service_risk_summary`, `configuration`, `meta`) with the exact columns/types specified there, **and** a module-level `threading.Lock()` wrapped by `execute(sql, params)` / `query(sql, params)` / `query_one(sql, params)` helper functions that acquire the lock for the duration of each call, with a docstring stating no other module may open a cursor or call the connection directly (per `research.md` §5 — required because FastAPI's default threadpool can call into the shared connection from multiple threads even for sequential single-user requests).
- [X] T003 Rewrite `sentinel-access/backend/app/seed_data.py`: instead of building Python-list `SeedData` attributes, load `server/data/synthetic-data.json` and `INSERT` its contents into the Phase-T002 SQLite tables (one seeding function called once at startup, per `data-model.md`). Keep the file reading `SEED_FILE` from the same path as today.
- [X] T004 Rewrite `sentinel-access/backend/app/store.py`'s **read** methods to query SQLite via `db.py`'s lock-serialized `query()`/`query_one()` helpers (never a raw cursor — per T002/`research.md` §5) instead of scanning Python lists, preserving every existing method's name/signature/return type exactly: `get_findings()`, `get_finding(id)`, `get_identities()`, `get_cloud_sources()`, `get_policies()`, `get_reports()`, `get_report(title)`, `get_configuration()`, `get_finding_explanation(id)`. Each still returns the same Pydantic model instances as before (constructed from the queried row(s)).
- [X] T005 [P] In `sentinel-access/backend/app/store.py`, add `@property` accessors for `model_rationale`, `access_trend`, `access_trend_peak_label`, `service_risk`, `service_risk_summary`, `findings`, `identities`, `policies` that query the Phase-T002 tables on access, so `command_center.py`'s and `main.py`'s existing direct-attribute reads (see "Important compatibility constraint" above) keep working unmodified. (Depends on T002-T004.)
- [X] T006 Rewrite `sentinel-access/backend/app/store.py`'s **mutation** methods to write to SQLite via `db.py`'s lock-serialized `execute()` helper (never a raw cursor — per T002/`research.md` §5): `update_finding_status(id, status)`, `add_finding(finding)`, `next_finding_id()`, `toggle_policy(title)`, `set_configuration(config)`, `cache_finding_explanation(id, text)`. Preserve existing behavior (e.g. `add_finding` still makes the new finding appear first in `get_findings()` ordering). (Depends on T002-T004.)
- [X] T007 Update `sentinel-access/backend/app/store.py`'s `get_store()` singleton so the one `Store` instance is created against the one `db.py` connection, calling the Phase-T003 seeding function exactly once per process (matching today's lazy-singleton behavior). (Depends on T003, T006.)

**Checkpoint**: Backend starts, seeds into SQLite, and every existing endpoint should behave exactly as before the storage swap (not yet verified — that's Story 1).

---

## Phase 3: User Story 1 - Backend state survives a rewrite of its storage engine unchanged (Priority: P1) 🎯 MVP

**Goal**: Every existing screen/endpoint returns identical values to the pre-migration behavior on a fresh backend start; finding-status/policy-toggle/configuration mutations still persist for the run.

**Independent Test**: Start the backend fresh, call every existing `/api/*` endpoint, and diff responses against the documented `001` seed values (per `quickstart.md` step 2); mutate a finding/policy/configuration and confirm the change is reflected on the next read (per `spec.md` US1 Acceptance Scenarios 2-3).

### Implementation for User Story 1

- [X] T008 [US1] Add `sentinel-access/backend/tests/integration/test_storage_parity.py`: on a fresh `TestClient`, assert `GET /api/command-center`, `GET /api/activity`, `GET /api/identities`, `GET /api/estate`, `GET /api/policies`, `GET /api/reports`, `GET /api/configuration` all match the documented seed values from `server/data/synthetic-data.json` (per spec US1 Acceptance Scenario 1 and `quickstart.md` step 2) — with the one documented exception of `summaryMetrics.activitiesChecked` (covered separately in Story 3).
- [X] T009 [US1] In the same test file, assert a finding status update (`POST /api/findings/{id}/status`), a policy toggle (`POST /api/policies/toggle`), and a configuration save each persist across subsequent `GET` calls within the same run (per spec US1 Acceptance Scenarios 2-3).
- [X] T010 [US1] Run `pytest tests/integration/test_storage_parity.py` and the full existing `tests/contract/` suite; fix any parity discrepancy found by adjusting `db.py`/`seed_data.py`/`store.py` (Phase 2 tasks) — do not change any router or schema file to make tests pass, since parity is the point of this story. (Depends on T002-T009.)

**Checkpoint**: Storage engine is swapped and behavior-preserving; existing test suite and new parity tests all pass.

---

## Phase 4: User Story 2 - Uploading a dataset adds to the activity history instead of replacing it (Priority: P1)

**Goal**: `POST /api/datasets` appends newly parsed records to the existing activity log; prior rows (seed and earlier uploads) are never lost; failed/empty uploads leave the log untouched.

**Independent Test**: Note the current activity log row count, upload a valid dataset file with N accepted records, confirm the log now has (previous count + N) rows with all prior rows intact; repeat for a second upload and confirm further accumulation (per `spec.md` US2 Acceptance Scenarios 1-3, `quickstart.md` step 3).

### Implementation for User Story 2

- [X] T011 [US2] In `sentinel-access/backend/app/store.py`, replace `replace_activity_log(events, source)` with `append_activity_events(events: list[ActivityEvent]) -> int`: `INSERT`s all given events into `activity_log` inside a single transaction, via `db.py`'s lock-serialized `execute()` helper (never a raw cursor — per T002/`research.md` §5), never deletes existing rows, sets `meta.activity_source = "imported"` if not already set, and returns the number of rows inserted (per `data-model.md` "Changed behavior 1" and `contracts/datasets.md`).
- [X] T012 [US2] Update `sentinel-access/backend/app/routers/datasets.py`'s `import_dataset` handler to call `store.append_activity_events(accepted)` instead of `store.replace_activity_log(accepted, "imported")`, keeping the existing `DatasetImportResult(acceptedCount=len(accepted), rejectedCount=len(errors), errors=errors[:20])` response describing only this upload (not the cumulative total) — per `contracts/datasets.md`. (Depends on T011.)
- [X] T013 [US2] [P] Update `sentinel-access/backend/tests/contract/test_datasets.py`'s assertions from replace-semantics to append-semantics (e.g. any test that currently asserts the log equals *only* the uploaded records must instead assert the uploaded records were added on top of what was already present), per `contracts/datasets.md`'s behavior-change table.
- [X] T014 [US2] Add `sentinel-access/backend/tests/integration/test_dataset_accumulation.py`: upload `datasets/synthetic-data.json` (the alternate flat `timestamp`/`user`/`action`/`sourceIp`/`service`/`status` schema) **three times in sequence** against one `TestClient`/backend run, and assert the activity log grows by each upload's `acceptedCount` every time (per spec SC-002's explicit "at least 3 consecutive uploads" requirement), with earlier rows from the seed and every prior upload still present unchanged after each subsequent upload (per spec US2 Acceptance Scenarios 1-3 and SC-004, `quickstart.md` step 3). Also assert an uploaded malformed/empty file leaves the log completely unchanged (per spec US2 Acceptance Scenario 4, FR-007). Also assert the upload does not create/modify any `Finding`, identity, policy, cloud source, or report (per FR-010), and that `needsAttention`/`mostUrgentCase` from `GET /api/command-center` are unchanged by any of the uploads (per FR-011).

**Checkpoint**: Dataset uploads accumulate correctly across multiple uploads in one run; failed uploads are no-ops.

---

## Phase 5: User Story 3 - The "activities checked" number reflects everything the system has actually seen (Priority: P2)

**Goal**: `summaryMetrics.activitiesChecked` is a live count of the activity log, growing by exactly N after any upload accepting N records, and unaffected by failed uploads.

**Independent Test**: Read Command Center summary metrics, upload a dataset with N new records, re-read summary metrics, confirm `activitiesChecked` increased by exactly N (per `spec.md` US3 Acceptance Scenarios 1-3, `quickstart.md` steps 2-4).

### Implementation for User Story 3

- [X] T015 [US3] In `sentinel-access/backend/app/store.py`'s `compute_summary_metrics()`, replace `activitiesChecked=self._seed.activities_checked_base` with a live `SELECT COUNT(*) FROM activity_log` query result, leaving every other field in that method (`needsAttention`, `mostUrgentCase`, `averageReviewTime`, `signalConfidencePct`, `identityCoveragePct`) unchanged (per `data-model.md` "Changed behavior 2" and `contracts/command-center.md`).
- [X] T016 [US3] [P] Update `sentinel-access/backend/tests/contract/test_command_center.py`'s expected `activitiesChecked` value from the old static `1482` to the live seeded row count (`6`, per `contracts/command-center.md`'s "At fresh startup" note). (Depends on T015.)
- [X] T017 [US3] Extend `sentinel-access/backend/tests/integration/test_dataset_accumulation.py` (from T014) to also assert `summaryMetrics.activitiesChecked` from `GET /api/command-center` increases by exactly each upload's `acceptedCount` after **each of the three sequential uploads**, and is unchanged after the malformed-file upload (per spec US3 Acceptance Scenarios 1-3, spec SC-002/SC-003, both requiring the ≥3-upload verification). (Depends on T014, T015.)

**Checkpoint**: All three user stories are implemented and independently verified; `activitiesChecked` is fully live.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final cleanup and end-to-end validation across all stories.

- [X] T018 [P] Remove any now-dead code left over from the Python-list `Store`/`SeedData` implementation in `sentinel-access/backend/app/seed_data.py` and `app/store.py` (e.g. unused imports, the old `_finding_id_counter`/list-based helpers if fully superseded by SQLite-backed equivalents).
- [X] T019 Run `pytest tests/contract tests/integration` in `sentinel-access/backend/` and confirm the full suite passes with no regressions.
- [X] T020 Manually execute `quickstart.md` steps 1-6 end-to-end against a running `uvicorn` instance and confirm the documented accumulation numbers (6 → 14 → 22 → 30) and the failed-upload no-op match exactly.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately.
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS all user stories (the entire storage swap must exist before any story's behavior is verifiable).
- **User Stories (Phase 3-5)**: All depend on Foundational phase completion.
  - US1 (Phase 3) has no dependency on US2/US3 and should be validated first (it's the parity baseline).
  - US2 (Phase 4) depends on Foundational only, but is easiest to verify meaningfully once US1's parity tests already pass (recommended sequential order, not a hard technical dependency).
  - US3 (Phase 5) touches the same `compute_summary_metrics()` method US1's parity test already exercises, and its integration test extends US2's upload test file (T014) — practically sequenced after US2, though the `activitiesChecked` formula change itself (T015) has no code dependency on US2.
- **Polish (Phase 6)**: Depends on all three user stories being complete.

### Within Each User Story

- Foundational data-layer changes (Phase 2) before any story's tests.
- Story implementation before that story's tests are expected to pass.
- Each story's checkpoint should be green before starting the next, to keep failures attributable to one story at a time.

### Parallel Opportunities

- T005 (property accessors) can run in parallel with finishing T006 (mutation methods) once T002-T004 are done — different concerns, same file, so coordinate if the same person isn't doing both.
- T013 and T016 (contract test updates) are `[P]` — different test files, no dependency on each other.
- T018 (dead-code cleanup) is `[P]` with T019/T020 since it doesn't block running the suite, though it's good practice to do it before the final polish test run.

---

## Parallel Example: Foundational Phase

```bash
# T002 must complete first (schema), then:
Task: "Rewrite seed_data.py to INSERT into SQLite tables (T003)"
# then in parallel:
Task: "Rewrite Store read methods to query SQLite (T004)"
Task: "Add Store @property accessors for direct-attribute call sites (T005)"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup.
2. Complete Phase 2: Foundational (CRITICAL — the entire storage swap).
3. Complete Phase 3: User Story 1 (parity verification).
4. **STOP and VALIDATE**: run `quickstart.md` steps 1-2; confirm zero behavior regressions.
5. This alone is a safe, demo-ready increment — the storage engine is swapped with no visible change.

### Incremental Delivery

1. Setup + Foundational → SQLite storage exists and is seeded.
2. Add User Story 1 → parity confirmed → safe checkpoint (deployable — no behavior change).
3. Add User Story 2 → dataset uploads accumulate → deployable (new, additive behavior).
4. Add User Story 3 → `activitiesChecked` goes live → deployable (completes the spec).
5. Polish → full regression pass + manual quickstart walkthrough.

## Notes

- [P] tasks touch different files (or, for T005, a clearly separable concern within the same file) with no blocking dependency between them.
- [Story] labels map every Phase 3-5 task to its `spec.md` user story for traceability.
- Commit after each task or logical group, per repository convention.
- Because Stories 2 and 3 both build on the same `store.py`/`activity_log` foundation and share one integration test file (T014 extended by T017), verify Story 1's checkpoint is green before starting Story 2, and Story 2's checkpoint before starting Story 3, even though a technically motivated team could work stories 2 and 3 in parallel branches.
