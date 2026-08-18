# Phase 1 Data Model: AI-Assisted Investigation Features

This extends `specs/001-fastapi-backend-migration/data-model.md` — entities
already defined there (`Finding`, `ActivityEvent`, `Identity`,
`ReportTemplate`, the `Store` shape) are reused unchanged. Only new/extended
shapes are documented here.

## FindingExplanation

Not a standalone stored entity — a cache entry keyed by `Finding.id` inside
the `Store`, and the response shape for the new explanation endpoint.

| Field | Type | Notes |
|---|---|---|
| `findingId` | `str` | matches `Finding.id` |
| `explanation` | `str` | plain-language narrative, either AI-generated or the fallback text |
| `source` | `Literal["ai", "fallback"]` | `"fallback"` when the AI call failed (FR-007) |

**Cache behavior** (FR-002): generated once per `Finding.id` on first
request, then served from `Store.finding_explanations` on every subsequent
request for the same finding, until backend restart.

## CopilotQuery / CopilotResponse

Not persisted — a per-request request/response pair for `POST
/api/copilot/query`.

**Request**

| Field | Type | Notes |
|---|---|---|
| `question` | `str` | the analyst's plain-English question |

**Response**

| Field | Type | Notes |
|---|---|---|
| `answer` | `str` | the model's plain-language answer (or a decline/unavailable message, FR-005/FR-007) |
| `findings` | `list[Finding]` | matching findings, if the question was about findings; `[]` otherwise |
| `activity` | `list[ActivityEvent]` | matching activity events; `[]` otherwise |
| `identities` | `list[Identity]` | matching identities; `[]` otherwise |

Result lists are populated by executing the tool call(s) the model chose
(see `research.md` §5) against the current `Store` state — never fabricated
by the model directly (FR-004).

## ReportNarrative

Not persisted — an additive field on the existing "prepare report" response
(`contracts/reports.md` in the 001 feature), generated fresh on every
"Prepare report" call (not cached, unlike `FindingExplanation`) so it always
reflects live data (FR-006, SC-005).

| Field | Type | Notes |
|---|---|---|
| `narrative` | `str \| None` | `None` when the AI call failed (FR-007) — the rest of the "prepared" response still succeeds |

## Store shape (extension)

```text
Store (additions on top of the 001 feature's shape)
└── finding_explanations: dict[str, str]   # cache keyed by Finding.id, per research.md §6
```

No other `Store` fields change. `ReportNarrative` and `CopilotResponse` are
computed per-request and intentionally not added to the `Store`, since they
must reflect live data on every call (report) or are inherently
per-question (copilot).
