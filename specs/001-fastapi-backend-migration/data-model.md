# Phase 1 Data Model: FastAPI Backend Migration

Entities and fields below are derived directly from the existing
`server/data/synthetic-data.json` fixture and the current frontend's usage of
it (`Home.tsx`, `WorkspaceViews.tsx`), per constitution Principle II
(preserve existing data shapes). Types are given as Python/Pydantic-style
annotations for the backend; the frontend already expects this shape today.

## Finding (Alert)

Represents one row in the Command Center investigation queue / Activity
Explorer detail.

| Field | Type | Notes |
|---|---|---|
| `id` | `str` | e.g. `"ALT-2841"`; stable identifier, used for status updates |
| `severity` | `Literal["Critical","High","Medium","Low"]` | drives `severityTone` styling |
| `title` | `str` | |
| `entity` | `str` | display name of the identity involved |
| `role` | `str` | |
| `source` | `str` | IP address or region string |
| `region` | `str` | |
| `service` | `str` | one of the cloud source names |
| `score` | `int` (0-100) | risk score |
| `time` | `str` | display time, e.g. `"08:42 UTC"` |
| `description` | `str` | |
| `signals` | `list[str]` | evidence chips |
| `baseline` | `str` | plain-language "what's normally expected" |
| `recommended` | `str` | recommended action text |
| `status` | `Literal["open","in_progress","escalated"] \| None` | `None`/`open` initially; mutated by FR-003 |

**State transitions** (FR-003): `open`/`None` → `in_progress` (start
investigation) or `open`/`None`/`in_progress` → `escalated` (escalate).
Transitions are one-way in this feature — there is no "reopen" action in any
user story.

**Validation**: `severity` and `score` are backend-owned (not user input in
this feature); the only mutation surface is `status` via a constrained enum.

## SummaryMetrics (KPIs)

Single object (not a list) backing the Command Center KPI banner.

| Field | Type |
|---|---|
| `activitiesChecked` | `int` |
| `needsAttention` | `int` |
| `mostUrgentCase` | `{ rank: str, label: str }` |
| `averageReviewTime` | `str` |
| `signalConfidencePct` | `float` |
| `identityCoveragePct` | `int` |

Derived server-side from the current `Finding` list state (e.g.
`needsAttention` = count of findings with `status` in `open`/`in_progress`)
so it stays consistent after status changes and simulated anomalies —
this is a computed view, not separately-stored state.

## ModelRationale

Single object backing the "model rationale" panel.

| Field | Type |
|---|---|
| `topFindingId` | `str` (references a `Finding.id`) |
| `explanation` | `str` |
| `signals` | `list[{ label: str, score: int, tone: str }]` |

## AccessTrendPoint

| Field | Type |
|---|---|
| `label` | `str` (hour label, e.g. `"00"`) |
| `events` | `int` |
| `anomalies` | `int` |

Returned as a list plus a sibling `accessTrendPeakLabel: str`.

## ServiceRisk

| Field | Type |
|---|---|
| `name` | `str` |
| `risk` | `int` (0-100) |
| `events` | `int` |

Returned as a list plus a sibling `serviceRiskSummary: { highestRiskService: str, sensitiveAssets: int, coverage: str }`.

## ActivityEvent

Backs Activity Explorer; also the shape produced by dataset import (FR-011).

| Field | Type |
|---|---|
| `time` | `str` |
| `actor` | `str` |
| `action` | `str` |
| `source` | `str` |
| `system` | `str` |
| `status` | `Literal["Needs attention","Review later","Normal"]` |
| `tone` | `Literal["critical","high","medium","normal"]` |

**Validation** (dataset import, FR-011): required fields `time`, `actor`,
`action`, `source`, `system`; `status`/`tone` are inferred with a documented
default (`"Normal"`/`"normal"`) if absent from an imported record, since
external datasets won't know the app's tone vocabulary. Max 10,000 records
per import (existing cap, carried over).

## Identity

| Field | Type |
|---|---|
| `name` | `str` |
| `initials` | `str` |
| `role` | `str` |
| `activity` | `str` (one-line "what looks unusual") |
| `score` | `int` (0-100) |
| `color` | `str` (hex, for risk badge) |
| `description` | `str` (baseline behavior) |

Identity Profiles' "activity timeline" (per FR-006) is derived server-side by
filtering `ActivityLog`/`Finding` entries where `actor`/`entity` matches the
identity's `name` — not separately stored.

## CloudSource

| Field | Type |
|---|---|
| `name` | `str` |
| `type` | `str` |
| `status` | `Literal["Connected","Disconnected"]` |
| `eventsToday` | `int` |
| `health` | `Literal["Healthy","Needs review","Limited history"]` |
| `icon` | `str` (icon identifier, passed through to frontend's icon map) |
| `color` | `str` (hex) |
| `dataFreshnessMin` | `int` |

Returned as a list plus a sibling `cloudSourcesOnline: int`.

## PolicyRule

| Field | Type |
|---|---|
| `title` | `str` (identifier for toggle requests — unique within the list) |
| `description` | `str` |
| `enabled` | `bool` |
| `category` | `str` |

**State transitions** (FR-008): `enabled` flips `true`/`false` via a toggle
request; no other fields are mutable.

## ReportTemplate

| Field | Type |
|---|---|
| `title` | `str` (identifier for "prepare" requests) |
| `detail` | `str` |
| `period` | `str` |
| `type` | `str` |

"Prepare report" (FR-009) does not change this entity's stored fields — it
returns a synchronous, backend-generated completion result (see
`contracts/reports.md`), consistent with the current demo-only behavior
noted in the spec's Assumptions.

## Configuration (Settings)

Single object, not a list.

| Field | Type |
|---|---|
| `notificationsEnabled` | `bool` |
| `plainLanguageExplanations` | `bool` |

**Validation** (FR-010): both fields are simple booleans; save replaces the
whole object.

## DatasetImportResult

Not persisted — a per-request response shape for FR-011.

| Field | Type |
|---|---|
| `acceptedCount` | `int` |
| `rejectedCount` | `int` |
| `errors` | `list[str]` (human-readable, one per rejected record or file-level issue) |

## Store shape (backend-internal)

```text
Store
├── findings: list[Finding]
├── model_rationale: ModelRationale
├── access_trend: list[AccessTrendPoint]
├── access_trend_peak_label: str
├── service_risk: list[ServiceRisk]
├── service_risk_summary: ServiceRiskSummary
├── activity_log: list[ActivityEvent]        # replaced wholesale on dataset import
├── identities: list[Identity]
├── cloud_sources: list[CloudSource]
├── policies: list[PolicyRule]
├── reports: list[ReportTemplate]
├── configuration: Configuration
└── activities_checked_base: int             # seed constant used in KPI derivation
```

`summaryMetrics` (KPIs) is intentionally **not** stored directly — it is
computed from `findings`/`activity_log` on each request so that a start-
investigation, escalate, or simulate-anomaly action is immediately reflected
without a separate update path to keep in sync (avoids a second source of
truth for the same numbers, per constitution Principle III).
