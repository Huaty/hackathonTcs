# Contract: Finding Explanations

Covers FR-001, FR-002, FR-007 (explanation portion), FR-008 (explanation portion).

## `GET /api/findings/{finding_id}/explanation`

Returns a plain-language explanation for the finding's evidence dossier,
generated from its `signals`/`baseline`/`description` on first request and
served from cache thereafter (see `data-model.md` — `FindingExplanation`).

**Response 200** (first request — generated fresh):
```json
{ "findingId": "ALT-2841", "explanation": "This access pattern was flagged because...", "source": "ai" }
```

**Response 200** (subsequent requests — served from cache): identical shape
and content to the first response for the same `finding_id`; no new
generation call is made.

**Response 200** (AI backend unreachable/errored — FR-007):
```json
{ "findingId": "ALT-2841", "explanation": "<finding's existing description/baseline text>", "source": "fallback" }
```

**Response 404**: `{ "detail": "Finding {finding_id} not found" }` if `finding_id` is unknown (matching the existing `GET /api/findings/{finding_id}` behavior).

## Errors

All error responses use FastAPI's default `{ "detail": "<message>" }` shape,
consistent with `contracts/command-center.md` in the 001 feature. A failure
to reach the AI backend is **not** surfaced as an HTTP error on this
endpoint — it degrades to the `"fallback"` response above (FR-007), so the
frontend never has to special-case an AI outage on this call.
