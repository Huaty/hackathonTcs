# Contract: Dataset Import

Covers FR-011.

## `POST /api/datasets`

Uploads a CSV or JSON file of activity records, validates and ingests it,
and replaces the store's active `activity_log` with the accepted records
(matching the existing "imported data replaces synthetic data for the
session" behavior from `CONTEXT.md`).

**Request**: `multipart/form-data` with a single `file` field.
- Accepted content types: `text/csv`, `application/json` (also inferred from
  file extension `.csv`/`.json` if `Content-Type` is generic).
- Max 10,000 records (existing cap, carried over per spec Assumptions).

**Response 200**:
```json
{ "acceptedCount": 842, "rejectedCount": 3, "errors": ["Row 17: missing required field 'actor'", "..."] }
```
On success (`acceptedCount > 0`), subsequent `GET /api/activity` calls return
`"source": "imported"` and the accepted records.

**Response 400**: file is unparseable (not valid CSV/JSON) or exceeds the
10,000-record cap — existing data is left unchanged.
```json
{ "detail": "File exceeds the 10,000 record limit (found 12,004)." }
```

**Response 422**: no file provided / wrong form field (FastAPI default).
