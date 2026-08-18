# Implementation Plan: FastAPI Backend Migration

**Branch**: `001-fastapi-backend-migration` | **Date**: 2026-08-18 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/001-fastapi-backend-migration/spec.md`

## Summary

Replace Sentinel Access's fully hardcoded frontend data with a new FastAPI backend
that serves the same six views (Command Center, Activity Explorer, Identity
Profiles, Cloud Estate, Policies, Reports/Configuration) and backs the same
interactive actions (start investigation, escalate, simulate anomaly, toggle
policy, prepare report, save settings, import dataset). The backend holds all
state in memory, seeded at startup from the existing `server/data/synthetic-data.json`
fixture, with no database and no authentication (per the project constitution).
The frontend switches from local hardcoded constants to REST calls against this
new service; the existing Express static server continues to serve the built SPA
and is not modified by this feature.

## Technical Context

**Language/Version**: Python 3.11+ for the backend (FastAPI); existing frontend stays TypeScript/React 19, unchanged.

**Primary Dependencies**: FastAPI, Uvicorn (ASGI server), Pydantic v2 (schemas/validation), `python-multipart` (CSV/JSON file upload parsing). Frontend continues to use its existing `axios` dependency for HTTP calls.

**Storage**: In-memory Python data structures only, seeded at process startup from `server/data/synthetic-data.json` (or a backend-local copy of the same shape). No database, no ORM, no migrations — per constitution Principle III.

**Testing**: `pytest` + FastAPI's `TestClient` (`httpx`) for backend contract and integration tests. Existing frontend testing (`vitest`) is unchanged and out of scope for this feature beyond manual verification that views render backend data correctly.

**Target Platform**: Local/dev server process (Uvicorn), same deployment class as the existing Node/Express server — no containerization or cloud-specific requirements introduced by this feature.

**Project Type**: Web application (existing frontend + new backend service).

**Performance Goals**: No explicit SLA requested; in-memory reads should feel instant for interactive dashboard use (informal target: well under 200ms per request on a dev machine), consistent with the current all-client-side experience it replaces.

**Constraints**: No authentication/authorization (constitution Principle III); no external database or services; existing 10,000-record dataset-import cap and CSV/JSON validation rules must carry over unchanged (spec Assumptions); response shapes must stay compatible with existing frontend prop/data expectations (constitution Principle II).

**Scale/Scope**: Single-process, single-instance demo/hackathon scale. Not designed for multi-tenant or high-concurrency production use; concurrent-session conflicts are resolved last-write-wins per spec Edge Cases.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Check | Result |
|---|---|---|
| I. API-First Backend Migration | Plan defines one backend endpoint group per existing view (Command Center, Activity Explorer, Identity Profiles, Cloud Estate, Policies, Reports/Configuration) plus dataset import, matching FR-001–FR-011. | PASS |
| II. Preserve Existing UX and Data Shapes | Data model (Phase 1) is derived directly from `server/data/synthetic-data.json` and current component prop shapes; no UI/visual changes planned. | PASS |
| III. Simplicity and YAGNI (NON-NEGOTIABLE) | Storage is in-memory only, seeded from existing JSON fixture; no DB, no auth, no external services introduced. | PASS |
| IV. Contract Clarity Before Implementation | Phase 1 produces `data-model.md` and `contracts/` before any implementation task is created (`/speckit-tasks` runs after this plan). | PASS |
| V. Demo-Safe Data Only | Seed data is the existing synthetic fixture; no real credentials/PII introduced. | PASS |

No violations — Complexity Tracking is not needed.

**Post-Design Re-check** (after Phase 1 `data-model.md`/`contracts/`/`quickstart.md`):
all 12 endpoints across `contracts/` are unauthenticated, stateless-except-for-the-
single-in-memory-`Store`, and every entity in `data-model.md` traces to an
existing field in `server/data/synthetic-data.json` or a value computed from
it (no new persisted entity was introduced). Gates I-V still PASS with no
new violations introduced by the detailed design.

## Project Structure

### Documentation (this feature)

```text
specs/001-fastapi-backend-migration/
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
├── client/                        # EXISTING frontend — unchanged structure
│   └── src/
│       ├── pages/Home.tsx         # switches from local fixtures to API calls
│       ├── components/WorkspaceViews.tsx
│       ├── components/DatasetImporter.tsx
│       └── lib/                   # NEW: api.ts (fetch/axios client for backend)
│
├── backend/                       # NEW: FastAPI service for this feature
│   ├── app/
│   │   ├── main.py                # FastAPI app, CORS, router registration
│   │   ├── seed_data.py           # loads server/data/synthetic-data.json at startup
│   │   ├── store.py                # in-memory state container (single source of truth)
│   │   ├── schemas/                # Pydantic models per entity (Finding, Identity, ...)
│   │   └── routers/
│   │       ├── command_center.py   # FR-001..FR-004
│   │       ├── activity.py         # FR-005
│   │       ├── identities.py       # FR-006
│   │       ├── estate.py           # FR-007
│   │       ├── policies.py         # FR-008
│   │       ├── reports.py          # FR-009
│   │       ├── configuration.py    # FR-010
│   │       └── datasets.py         # FR-011
│   ├── tests/
│   │   ├── contract/               # one test module per router, asserts response schema
│   │   └── integration/            # cross-endpoint flows (e.g. start investigation -> GET reflects it)
│   └── requirements.txt (or pyproject.toml)
│
└── server/                        # EXISTING Express static file server — unmodified by this feature
```

**Structure Decision**: Add a new `sentinel-access/backend/` FastAPI service rather than
extending the existing `server/` Express app. During development, Uvicorn runs the
backend on its own port (default `8001`) and the Vite dev server proxies
`/api/*` to it (`vite.config.ts` `server.proxy`), so the frontend can call
relative `/api/...` paths in both dev and any future production setup. The
existing Express server (`server/index.ts`) keeps its current, narrower job —
serving the built SPA — and is not extended with API routes; how the FastAPI
process is run/deployed in production is intentionally left open (out of
scope for this feature, which targets local/dev functionality per its
success criteria).

## Complexity Tracking

*No constitution violations — not applicable.*
