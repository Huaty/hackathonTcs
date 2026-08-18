# Contract: Activity Explorer

Covers FR-005.

## `GET /api/activity`

Returns the current activity log — either the seeded dataset or the most
recently imported dataset (FR-005, tied to FR-011).

**Query params** (optional, all server-side filtering to keep the frontend simple):
- `search: str` — matches against `actor`/`action`/`source` (case-insensitive substring)
- `status: Literal["Needs attention","Review later","Normal"]`

**Response 200**:
```json
{
  "events": [ /* ActivityEvent[], see data-model.md */ ],
  "source": "seed" | "imported"
}
```
`source` tells the frontend whether it's viewing seed or imported data (surfacing the
existing "data lifecycle" transparency requirement from `CONTEXT.md`).
