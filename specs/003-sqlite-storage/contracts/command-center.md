# Contract delta: Command Center (supersedes only the `activitiesChecked` note in `001-fastapi-backend-migration/contracts/command-center.md`)

Covers spec FR-009. Route, method, and every other field are unchanged from
`001` — see `001`'s `contracts/command-center.md` for the full response
shape.

## `GET /api/command-center`

`summaryMetrics.activitiesChecked` is now computed as the live row count of
`activity_log` (`SELECT COUNT(*) FROM activity_log`) instead of a fixed
seed constant.

- **At fresh startup**: equals the seed file's `activityLog` array length
  (currently 6 rows in `server/data/synthetic-data.json`) — this is smaller
  than the seed file's separate, no-longer-used
  `summaryMetrics.activitiesChecked` demo value (1482); see
  `data-model.md`'s "Changed behavior 2" section for why.
- **After any successful `POST /api/datasets` upload accepting N records**:
  increases by exactly N on the next `GET /api/command-center` call.
- **After a failed/zero-record upload**: unchanged.

No other field in the Command Center response is affected by this feature.
