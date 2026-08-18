# Contract: Dataset Import (supersedes `001-fastapi-backend-migration/contracts/datasets.md`)

Covers spec FR-005 through FR-008.

## `POST /api/datasets`

Uploads a CSV or JSON file of activity records, validates and normalizes it
(field-alias matching unchanged from `001`), and **appends** the accepted
records to the store's `activity_log` — it no longer replaces prior
contents. Request shape, content-type handling, and the 10,000-record
per-file cap are all unchanged from `001`.

**Request**: `multipart/form-data` with a single `file` field. Unchanged
from `001`. Also accepts files in the alternate flat schema exemplified by
`timestamp`/`user`/`action`/`sourceIp`/`service`/`status` fields (already
covered by the existing `FIELD_ALIASES` matching in `datasets.py` — no
parser change required).

**Response 200** (unchanged shape):
```json
{ "acceptedCount": 8, "rejectedCount": 1, "errors": ["Row 9: empty record"] }
```
`acceptedCount`/`rejectedCount` describe **this upload only**, not the
cumulative activity log size. On success (`acceptedCount > 0`):
- The accepted records are added to the existing `activity_log` (seed rows
  and any prior uploads' rows remain present and unchanged).
- Subsequent `GET /api/activity` calls return `"source": "imported"` and
  the full, now-larger, event list.
- Subsequent `GET /api/command-center` calls return a `summaryMetrics.activitiesChecked`
  that has increased by exactly `acceptedCount` (see `command-center.md` delta).

**Response 400**: file is unparseable, contains zero usable records, or
exceeds the 10,000-record cap — **existing data is left completely
unchanged** (nothing is appended; unchanged from `001`'s "existing data is
left unchanged" guarantee, just re-scoped from "replace" semantics to
"append" semantics).
```json
{ "detail": "File exceeds the 10,000 record limit (found 12,004)." }
```

**Response 422**: no file provided / wrong form field (FastAPI default,
unchanged).

## Behavior change summary vs. `001`

| Aspect | `001` (before) | `003` (this feature) |
|---|---|---|
| Effect on existing `activity_log` rows | Replaced entirely | Preserved; new rows appended |
| Repeated uploads in one run | Each upload wholly replaces the last | Each upload adds on top of all previous uploads + seed |
| `acceptedCount` meaning | Also happened to equal the resulting log size (since log was replaced) | Only this upload's count — resulting log size is `acceptedCount` + everything already present |
