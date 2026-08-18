# Contract: Ask Sentinel Copilot

Covers FR-003, FR-004, FR-005, FR-007 (copilot portion), FR-008 (copilot portion), FR-010.

## `POST /api/copilot/query`

Accepts a plain-English question and returns an answer plus the specific
records (if any) that support it, drawn only from current in-memory `Store`
state (findings, activity log, identities) via bounded tool-calling — see
`research.md` §5.

**Request body**:
```json
{ "question": "show me high-risk findings on AWS IAM this week" }
```

**Response 200** (question matched data):
```json
{
  "answer": "There are 3 high-risk findings on AWS IAM: ...",
  "findings": [ /* Finding[], see 001 feature's data-model.md */ ],
  "activity": [],
  "identities": []
}
```

**Response 200** (no matching records — FR-005): `answer` clearly states no
matches were found; all three list fields are `[]`. Not a 404 — an empty
result is a valid, successful answer to a valid question.

**Response 200** (out-of-scope question — FR-005): `answer` politely
declines and states the assistant only answers questions about the current
security data; all three list fields are `[]`.

**Response 200** (AI backend unreachable/errored — FR-007):
```json
{ "answer": "The AI assistant is unavailable right now — try the search and filter controls instead.", "findings": [], "activity": [], "identities": [] }
```
Returned as 200, not 5xx, so the frontend renders it as a normal (if
disappointing) response rather than triggering an error boundary; the
existing manual search/filter controls remain usable regardless (FR-007).

**Response 422**: empty/missing `question` (FastAPI's default validation
error shape, per the 001 feature's `contracts/*.md` convention).

## Errors

All error responses use FastAPI's default `{ "detail": "<message>" }` shape.
As with the explanations endpoint, an AI-backend outage is represented as a
200 with a decline message, not an HTTP error — see the response case above.
