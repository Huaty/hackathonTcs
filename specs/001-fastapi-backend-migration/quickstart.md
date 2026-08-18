# Quickstart: FastAPI Backend Migration

Validates that the backend serves live data and the frontend consumes it,
per the spec's Success Criteria.

## Prerequisites

- Python 3.11+ with `pip` (or `uv`)
- Node/pnpm already set up for `sentinel-access/client` (existing project)

## 1. Run the backend

```bash
cd sentinel-access/backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8001
```

Expected: startup log shows the seed data loaded (e.g. finding/identity/policy counts).

## 2. Run the frontend (dev, with proxy to the backend)

```bash
cd sentinel-access
pnpm install
pnpm dev
```

Expected: Vite serves the SPA on its usual dev port; `/api/*` calls are
proxied to `http://localhost:8001` (per `research.md` §3).

## 3. Validate SC-001 — views run on live data

- Open the Command Center. In a separate terminal, hit
  `GET http://localhost:8001/api/command-center` directly and confirm the
  KPI numbers match what's rendered in the UI.
- Repeat for Activity Explorer (`/api/activity`), Identity Profiles
  (`/api/identities`), and Cloud Estate (`/api/estate`).

## 4. Validate SC-002 — status changes persist server-side

- In the Command Center, open a finding's evidence dossier and click "Start
  investigation."
- Confirm the queue shows "In progress" for that finding.
- Reload the browser page fully (not a client-side re-render) and confirm
  the finding still shows "In progress" — proves the status lives in the
  backend `Store`, not local React state.

## 5. Validate SC-003 — dataset import flow

- Use the existing dataset importer UI to upload a small valid CSV.
- Confirm the response summary (accepted/rejected counts) is shown.
- Confirm Activity Explorer now reflects the imported records
  (`GET /api/activity` returns `"source": "imported"`).
- Try uploading a malformed file and confirm a clear validation error is
  shown without corrupting the previously accepted dataset.

## 6. Validate SC-004 — backend-unreachable behavior

- Stop the backend process (`Ctrl+C` on the Uvicorn process).
- Reload any view in the frontend and confirm it shows a clear loading/error
  state rather than blank content or stale hardcoded values.

## 7. Validate SC-005 — fresh-start parity with today's demo

- Restart the backend with no dataset imported and no status changes made.
- Confirm the Command Center KPI banner and queue composition match today's
  hardcoded values (from `server/data/synthetic-data.json`), proving the
  migration is a like-for-like data-source swap.

## Automated checks (backend)

```bash
cd sentinel-access/backend
pytest tests/contract      # one module per router, response-shape assertions
pytest tests/integration   # e.g. start-investigation-then-refetch flow
```
