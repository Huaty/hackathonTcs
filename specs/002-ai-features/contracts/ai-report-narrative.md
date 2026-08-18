# Contract: AI Report Narratives

Covers FR-006, FR-007 (report portion), FR-008 (report portion). This is an
**additive extension** of `POST /api/reports/{title}/prepare` from the 001
feature's `contracts/reports.md` (implemented as part of 001's pending User
Story 3 / T028) — the existing response fields are unchanged; one field is
added.

## `POST /api/reports/{title}/prepare` (extended)

**Request body**: none (unchanged from the 001 contract).

**Response 200** (AI narrative generated successfully):
```json
{
  "title": "Today's security summary",
  "status": "ready",
  "preparedAt": "2026-08-18T08:45:18Z",
  "narrative": "Today's activity showed 3 findings requiring review, concentrated in AWS IAM..."
}
```
`narrative` is generated fresh on every call from current `findings`/
`activity_log` state (not cached) — per FR-006/SC-005, preparing the same
report again after new findings appear MUST produce a different narrative
reflecting the update.

**Response 200** (AI backend unreachable/errored — FR-007):
```json
{
  "title": "Today's security summary",
  "status": "ready",
  "preparedAt": "2026-08-18T08:45:18Z",
  "narrative": null
}
```
The report-prepare action still completes successfully (`status: "ready"`)
even when narrative generation fails — the AI addition must never block the
existing non-AI confirmation the action already provides.

**Response 404**: unknown report `title` (unchanged from the 001 contract).

## Errors

Unchanged from the 001 `contracts/reports.md` — FastAPI's default
`{ "detail": "<message>" }` shape. An AI-backend outage is represented by
`narrative: null` on an otherwise-200 response, not an HTTP error.
