# Contract: Command Center

Covers FR-001 through FR-004.

## `GET /api/command-center`

Returns everything the Command Center view needs in one call.

**Response 200**:
```json
{
  "summaryMetrics": { "activitiesChecked": 1482, "needsAttention": 17,
    "mostUrgentCase": { "rank": "01", "label": "Unusual permission change" },
    "averageReviewTime": "4m 18s", "signalConfidencePct": 94.2, "identityCoveragePct": 87 },
  "findings": [ /* Finding[], see data-model.md */ ],
  "modelRationale": { "topFindingId": "ALT-2841", "explanation": "...", "signals": [ /* ... */ ] },
  "accessTrend": [ /* AccessTrendPoint[] */ ],
  "accessTrendPeakLabel": "18:00 UTC",
  "serviceRisk": [ /* ServiceRisk[] */ ],
  "serviceRiskSummary": { "highestRiskService": "IAM", "sensitiveAssets": 31, "coverage": "8 / 8" }
}
```
`summaryMetrics` is computed from current `findings`/`activity_log` state (see data-model.md), not stored separately.

## `GET /api/findings/{finding_id}`

Returns full evidence-dossier detail for one finding (FR-002).

- **200**: a single `Finding` object.
- **404**: `{ "detail": "Finding {finding_id} not found" }` if `finding_id` is unknown.

## `POST /api/findings/{finding_id}/status`

Updates a finding's status (FR-003) — backs both "Start investigation" and "Escalate".

**Request body**:
```json
{ "status": "in_progress" }
```
`status` MUST be one of `"in_progress"`, `"escalated"`.

**Response 200**: the updated `Finding` object.

**Response 404**: unknown `finding_id`.

**Response 422**: invalid `status` value (FastAPI's default validation error shape).

## `POST /api/findings/simulate-anomaly`

Injects a synthetic high-severity finding into the queue (FR-004), backing the "Simulate anomaly" action.

**Request body**: none.

**Response 201**: the newly created `Finding` object (generated `id`, plausible synthetic
severity/entity/signals consistent with existing seed examples).

## Errors

All error responses use FastAPI's default `{ "detail": "<message>" }` shape (FR-016).
