# Phase 0 Research: FastAPI Backend Migration

All items in the Technical Context were resolvable from the constitution, the
spec's own assumptions, and the existing codebase — no items were left as
`NEEDS CLARIFICATION`. This document records the decisions and alternatives
considered for the choices that had more than one reasonable option.

## 1. In-memory state pattern

**Decision**: A single module-level `Store` object (in `backend/app/store.py`)
holding plain Python objects (dataclasses or dicts), constructed once at app
startup from `seed_data.py`, and mutated in place by router handlers via
simple methods (e.g. `store.update_finding_status(id, status)`).

**Rationale**: Constitution Principle III forbids a database; FastAPI's
dependency-injection system can hand out a reference to the same process-wide
store instance to every request without extra infrastructure. This keeps
reads/writes trivially consistent within one process, which matches the
"single-instance demo" scope in Technical Context.

**Alternatives considered**:
- *SQLite in-memory (`:memory:`) via SQLAlchemy* — rejected: adds an ORM and
  session-management layer for no benefit at this scale, and conflicts with
  Principle III's explicit "no ORM" constraint.
- *Per-request fresh copy of seed data* — rejected: would make status changes
  (start investigation, policy toggles, etc.) not persist across requests,
  failing FR-003/SC-002 directly.

## 2. Dataset re-seeding vs. reset endpoint

**Decision**: No reset endpoint in this feature; seed data loads once at
process startup. Restarting the Uvicorn process is the documented way to
return to defaults (already captured in spec Edge Cases).

**Rationale**: Spec explicitly treats backend-restart-clears-state as expected
behavior, so no additional "reset" API is required by any functional
requirement.

**Alternatives considered**: A `POST /api/dev/reset` endpoint — rejected as
out of scope; nothing in the spec's user stories calls for it, and adding it
would violate YAGNI (Principle III).

## 3. Frontend-to-backend connection in dev

**Decision**: Vite dev server proxy (`server.proxy` in `vite.config.ts`)
forwards `/api/*` to `http://localhost:8001`; the FastAPI app also enables
permissive CORS (`allow_origins=["*"]`) as a fallback so the frontend works
even without the proxy (e.g. if run against a deployed backend later).

**Rationale**: Keeps frontend code free of hardcoded backend hostnames/ports
(calls stay relative, e.g. `/api/command-center`), which is the standard Vite
pattern and requires no new frontend dependency (axios already present).

**Alternatives considered**: Hardcoded `http://localhost:8001` base URL in an
env var consumed by the frontend — viable, but the proxy approach is simpler
for this demo scope and avoids an extra `.env` requirement; documented here in
case CORS-only usage without the proxy is preferred later.

## 4. CSV/JSON dataset upload handling

**Decision**: A single `POST /api/datasets` endpoint accepting
`multipart/form-data` (via `python-multipart`), branching on file extension /
`Content-Type` to parse CSV (Python stdlib `csv` module) or JSON
(`json.loads`), validating each record against the same rules the existing
`DatasetImporter.tsx` enforces client-side (structure, 10,000-record cap),
and replacing the store's "active activity dataset" on success.

**Rationale**: Matches FR-011 and preserves current behavior described in
`CONTEXT.md` ("imported data replaces synthetic data for the session").
`python-multipart` is FastAPI's documented, minimal dependency for file
uploads — no additional parsing library needed for CSV/JSON.

**Alternatives considered**: Accepting a raw JSON body with a
pre-parsed-on-the-client array — rejected: would require duplicating
CSV-parsing logic in the frontend (defeats the purpose of moving validation
server-side) and diverges from a natural file-upload contract.

## 5. Testing approach

**Decision**: `pytest` with FastAPI's built-in `TestClient` (backed by
`httpx`) for both contract tests (one module per router, asserting response
shape/status codes) and integration tests (multi-call flows, e.g. start
investigation then re-fetch and assert persisted status).

**Rationale**: This is FastAPI's standard, dependency-light testing story;
no test database or fixtures beyond the same in-memory seed are needed.

**Alternatives considered**: None seriously considered — this is the
established convention for FastAPI projects and introduces no extra
infrastructure.

## Summary

No unresolved unknowns remain. Proceeding to Phase 1 (data-model.md,
contracts/, quickstart.md).
