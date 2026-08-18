# Quickstart: SQLite In-Memory Storage & Additive Dataset Uploads

Validates that the SQLite-backed store is behavior-preserving on fresh
startup, and that dataset uploads append rather than replace, per the
spec's Success Criteria.

## Prerequisites

- Python 3.11+ with `pip` (backend already set up per
  `001-fastapi-backend-migration/quickstart.md`)
- Two sample files to upload: `sentinel-access/server/data/synthetic-data.json`
  (the seed shape — not typically re-uploaded, but useful as a schema
  contrast) and `datasets/synthetic-data.json` (the alternate flat schema
  this feature specifically targets)

## 1. Run the backend

```bash
cd sentinel-access/backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8001
```

Expected: startup log shows the same seeded counts as before this feature
(finding/identity/policy counts unchanged — SQLite seeding produces
identical row counts to the old Python-list seeding).

## 2. Validate SC-001 — fresh startup is unchanged

```bash
curl http://localhost:8001/api/command-center
curl http://localhost:8001/api/activity
```

- Confirm every field matches `001`'s documented seed values, **except**
  `summaryMetrics.activitiesChecked`, which is now `6` (the literal count
  of `activityLog` rows in the seed file) instead of `1482` (the seed
  file's old static demo constant) — see `data-model.md`'s "Changed
  behavior 2".

## 3. Validate SC-002 — uploads accumulate across multiple requests

Spec SC-002 requires accumulation to be verified across **at least 3**
consecutive uploads in the same run, not just one — so this step uploads
the same file three times:

```bash
curl -F "file=@../../datasets/synthetic-data.json" http://localhost:8001/api/datasets
curl http://localhost:8001/api/command-center | grep activitiesChecked
curl -F "file=@../../datasets/synthetic-data.json" http://localhost:8001/api/datasets
curl http://localhost:8001/api/command-center | grep activitiesChecked
curl -F "file=@../../datasets/synthetic-data.json" http://localhost:8001/api/datasets
curl http://localhost:8001/api/command-center | grep activitiesChecked
```

- First upload: response reports `acceptedCount` for that file (expect 8 —
  8 valid records; the file's 9th entry is an empty object and is
  rejected, per `datasets/synthetic-data.json`'s current contents).
- `activitiesChecked` after upload 1: `6 + 8 = 14`.
- Second upload (same file again, no de-dup by design): `acceptedCount` is
  again 8. `activitiesChecked` after upload 2: `14 + 8 = 22`.
- Third upload: `acceptedCount` is again 8. `activitiesChecked` after
  upload 3: `22 + 8 = 30` — proves accumulation across at least 3
  consecutive uploads in the same run, not just a single-upload bump.

## 4. Validate SC-003 — failed upload leaves state unchanged

```bash
echo '{not valid json' > /tmp/bad.json
curl -F "file=@/tmp/bad.json" http://localhost:8001/api/datasets   # expect 400
curl http://localhost:8001/api/command-center | grep activitiesChecked
```

- Confirm the response is a 400 with a clear error and `activitiesChecked`
  is unchanged from before this request (still 30 if run immediately after
  step 3).

## 5. Validate SC-004 — nothing already visible disappears

```bash
curl http://localhost:8001/api/activity | jq '.events | length'
```

- Confirm the count matches the cumulative total from step 3 (30), and
  that the first 6 rows (the original seed rows) are still present
  unchanged in the response.

## 6. Validate SC-005 — existing test suite still passes

```bash
cd sentinel-access/backend
pytest tests/contract
pytest tests/integration
```

Expected: all tests pass; `tests/contract/test_datasets.py` and any new
tests reflect append-not-replace semantics per `contracts/datasets.md`.
