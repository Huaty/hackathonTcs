# Contract: Reports

Covers FR-009.

## `GET /api/reports`

**Response 200**:
```json
{ "reports": [ /* ReportTemplate[], see data-model.md */ ] }
```

## `POST /api/reports/{title}/prepare`

Backs the "Prepare report" action. Demo-only (per spec Assumptions): no real
file is generated; the backend returns a synchronous completion result.

**Request body**: none.

**Response 200**:
```json
{ "title": "Today's security summary", "status": "ready", "preparedAt": "2026-08-18T08:45:18Z" }
```

**Response 404**: unknown report `title`.

## `GET /api/reports/export.csv`

Backs the existing global "Export activity CSV" action — streams the current
`activity_log` (seed or imported) as CSV.

**Response 200**: `text/csv` body, `Content-Disposition: attachment; filename="activity-export.csv"`.
