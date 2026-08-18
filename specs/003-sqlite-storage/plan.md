# Implementation Plan: SQLite In-Memory Storage & Additive Dataset Uploads

**Branch**: `003-sqlite-storage` | **Date**: 2026-08-18 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/003-sqlite-storage/spec.md`

## Summary

Replace `sentinel-access/backend/app/store.py`'s in-memory Python object `Store`
(lists of Pydantic models) with a single-process, in-memory SQLite database
(`sqlite3`, `:memory:`), still seeded at startup from the existing
`server/data/synthetic-data.json` fixture. Every entity currently held by
`Store` moves to a SQLite table behind the same public `Store` interface, so
every router (`command_center`, `activity`, `identities`, `estate`,
`policies`, `reports`, `configuration`, `datasets`, `copilot`) is unaffected
at the call-site level — only `store.py`'s internals and `seed_data.py`'s
load path change. On top of that swap, `POST /api/datasets` changes from
replacing the activity log wholesale to appending newly parsed records into
the `activity_log` table, and `summaryMetrics.activitiesChecked` changes from
a static seed constant to a live `SELECT COUNT(*)` over that table.

## Technical Context

**Language/Version**: Python 3.11+ (backend, unchanged). Frontend untouched by this feature.

**Primary Dependencies**: Python's built-in `sqlite3` module (standard library — no new third-party dependency). FastAPI/Pydantic v2/Uvicorn/`python-multipart` unchanged from `001-fastapi-backend-migration`.

**Storage**: SQLite, single in-process connection to `:memory:`, created and seeded once per server run inside `store.py`/`seed_data.py`. Not a file on disk, not a networked/hosted database. Pydantic models remain the request/response (API) schema layer; SQLite rows are an internal storage detail, mapped to/from Pydantic models at the `Store` boundary so router code and `schemas/entities.py` need no changes.

**Testing**: `pytest` + FastAPI `TestClient`, same as today. Existing contract tests (`tests/contract/*`) must keep passing unmodified in their assertions (only fixture/setup code may need to change if it currently pokes at `Store` internals). New tests cover: fresh-seed parity, append-on-upload accumulation across multiple uploads, `activitiesChecked` tracking the row count, and unchanged-on-failed-upload behavior.

**Target Platform**: Same local/dev Uvicorn process as today — no deployment change.

**Project Type**: Web application (existing frontend + backend service); this feature is backend-only.

**Performance Goals**: No new SLA. In-memory SQLite reads/writes for this data volume (tens to low-thousands of rows) are sub-millisecond; no measurable regression versus the current Python-list scans expected.

**Constraints**: Must preserve every existing response shape/value exactly on fresh startup (spec SC-001). Existing 10,000-record upload cap and field-alias normalization in `datasets.py` carry over unchanged. No authentication, no external services (constitution Principles III/V). Single-process, single SQLite connection shared across FastAPI's request threadpool — reads and writes are serialized through a single `threading.Lock` in `app/db.py` (per `research.md` §5) rather than assumed to be safe by virtue of being "single-process"; FastAPI's default sync-route threadpool means concurrent-thread access to the shared connection is a real possibility even for a single user's sequential-looking requests.

**Scale/Scope**: Same demo/hackathon single-instance scale as `001-fastapi-backend-migration`; activity log is expected to grow by at most a few thousand rows per upload, well within SQLite in-memory capacity.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Check | Result |
|---|---|---|
| I. API-First Backend Migration | No endpoint is added, removed, or renamed; all existing view-to-endpoint mappings from `001` are untouched. `POST /api/datasets`'s behavior changes (append vs. replace) but its route/contract shape does not. | PASS |
| II. Preserve Existing UX and Data Shapes | `data-model.md` (Phase 1) keeps every existing entity's field names/types identical; SQLite is purely an internal representation change behind `Store`, translated back to the same Pydantic response models. | PASS |
| III. Simplicity and YAGNI (NON-NEGOTIABLE) | See Complexity Tracking below — this principle's literal text ("MUST NOT introduce a database... no SQL... no external DB engine") is in tension with using SQLite, even in-memory. Justified as a bounded, explicitly-approved exception; no ORM, no migrations, no external DB *service*, no auth added. | JUSTIFIED EXCEPTION (see Complexity Tracking) |
| IV. Contract Clarity Before Implementation | Phase 1 produces an updated `data-model.md` (SQLite schema + mapping) and confirms `contracts/` (only `POST /api/datasets`'s narrative changes) before `/speckit-tasks` runs. | PASS |
| V. Demo-Safe Data Only | Seed source remains `server/data/synthetic-data.json`; upload path continues to accept only files the user supplies (e.g. the fictitious `datasets/synthetic-data.json`), no real data introduced by this feature. | PASS |

**Complexity Tracking is required** (see below) because of the Principle III tension — proceeding to Phase 0 research to confirm the in-memory-SQLite reading is sound before finalizing design.

**Post-Design Re-check** (after Phase 1 `data-model.md`/`contracts/`/`quickstart.md`):
`data-model.md` confirms every table is a 1:1 mapping of an existing
Pydantic entity with no new API-visible fields, `Store`'s public method
signatures are unchanged except the one call (`replace_activity_log` →
`append_activity_events`) the spec explicitly requires, and both
`contracts/` deltas document only the two spec-required behavior changes
(append semantics, live `activitiesChecked`) with everything else marked
unchanged from `001`. No new violation was introduced by the detailed
design beyond the single, already-justified Principle III exception. Gates
I, II, IV, V still PASS; III remains a JUSTIFIED EXCEPTION as recorded
above.

## Project Structure

### Documentation (this feature)

```text
specs/003-sqlite-storage/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
sentinel-access/
├── client/                        # UNCHANGED by this feature
│
├── backend/
│   ├── app/
│   │   ├── main.py                 # UNCHANGED (router registration, lifespan)
│   │   ├── db.py                   # NEW: sqlite3 :memory: connection factory, schema DDL, lock-serialized execute()/query() helpers (research.md §5)
│   │   ├── seed_data.py            # CHANGED: loads synthetic-data.json and INSERTs into SQLite tables instead of building Python lists
│   │   ├── store.py                # CHANGED: same public method signatures, internals now issue SQL against db.py's connection
│   │   ├── schemas/entities.py     # UNCHANGED (API-facing Pydantic models)
│   │   └── routers/
│   │       ├── datasets.py         # CHANGED: calls a new Store.append_activity_events(...) instead of replace_activity_log(...)
│   │       └── (all other routers) # UNCHANGED — consume Store's existing public methods
│   ├── tests/
│   │   ├── contract/
│   │   │   └── test_datasets.py    # CHANGED: assertions updated for append-not-replace + live activitiesChecked
│   │   └── integration/
│   │       └── test_dataset_accumulation.py  # NEW: multi-upload accumulation + activitiesChecked growth (Stories 2 & 3)
│   └── requirements.txt            # UNCHANGED (sqlite3 is stdlib)
│
└── server/                        # UNCHANGED
```

**Structure Decision**: No new top-level project or service — this feature
modifies the existing `sentinel-access/backend/` FastAPI service in place.
A new `app/db.py` module owns the SQLite connection and schema (single
`:memory:` connection created once at process startup and held for the
process lifetime, matching the existing single-`Store`-singleton pattern in
`store.py`'s `get_store()`); `seed_data.py` and `store.py` are rewritten
around it, but every router, every Pydantic schema in `schemas/entities.py`,
and every existing endpoint's request/response contract stay exactly as
specified in `001-fastapi-backend-migration`'s `data-model.md` and
`contracts/`, except for the two explicitly-scoped changes to
`POST /api/datasets` and `activitiesChecked` covered by this feature's spec.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|---------------------------------------|
| Introduces SQLite (a SQL database engine), where Principle III says "MUST NOT introduce a database... no SQL." | The user explicitly requested SQLite as the storage mechanism for this feature, specifically to get relational append/aggregate semantics (`SELECT COUNT(*)` for live `activitiesChecked`, appending rows across uploads) that are awkward to hand-roll correctly and are easy to get subtly wrong with ad hoc list mutation (e.g. accidentally sharing/aliasing list references, forgetting to re-derive a count in one of several call sites). | Continuing with a plain Python list (Principle III's literal preference) was considered and rejected only because it was not what was asked for here — functionally, append-and-count is fully achievable with a Python list too. This plan resolves the tension by keeping the *spirit* of Principle III intact: the SQLite instance is `:memory:`-only (no file, no server process, no network dependency, no external service to install/run/fail), requires no ORM and no migrations, adds no authentication, and is fully encapsulated behind the existing `Store` class so no router or schema code depends on SQL directly. It is treated as an internal data-structure choice inside the same single-process demo, not as "infrastructure" in the sense Principle III guards against (setup cost, external failure surface). Recommendation carried into Phase 0 research: confirm no simpler stdlib-only approach was overlooked, and flag this reading explicitly to the user/constitution owner as a candidate for a future Principle III amendment if SQLite proves to want to stay long-term. |
