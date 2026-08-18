# Phase 1 Data Model: SQLite In-Memory Storage & Additive Dataset Uploads

This feature does not change any API-facing entity shape defined in
`specs/001-fastapi-backend-migration/data-model.md` — every Pydantic model
in `sentinel-access/backend/app/schemas/entities.py` keeps its existing
fields/types. What changes is the **internal storage representation**
behind `Store` (Python lists → SQLite tables) and two **derived-value
semantics** (`activitiesChecked`, dataset-upload persistence mode). This
document covers only the delta: the SQLite schema, the mapping to existing
Pydantic models, and the two changed behaviors.

## SQLite schema (internal, not API-visible)

One connection, `sqlite3.connect(":memory:")`, opened once at process
startup and held for the process lifetime (module-level singleton in
`app/db.py`, mirroring today's `get_store()` singleton pattern).

| Table | Columns | Notes |
|---|---|---|
| `findings` | `id TEXT PRIMARY KEY`, `severity TEXT`, `title TEXT`, `entity TEXT`, `role TEXT`, `source TEXT`, `region TEXT`, `service TEXT`, `score INTEGER`, `time TEXT`, `description TEXT`, `signals TEXT` (JSON array), `baseline TEXT`, `recommended TEXT`, `status TEXT NULL` | Maps 1:1 to `Finding`. Insert order preserved via an implicit `rowid`; `add_finding` still inserts new rows "first" for display purposes by sorting on rowid DESC where the current code does `list.insert(0, ...)`. |
| `activity_log` | `id INTEGER PRIMARY KEY AUTOINCREMENT`, `time TEXT`, `actor TEXT`, `action TEXT`, `source TEXT`, `system TEXT`, `status TEXT`, `tone TEXT` | Maps 1:1 to `ActivityEvent` plus an internal-only `id`/insertion-order column (never serialized in API responses). This is the table `activitiesChecked` counts and that dataset upload appends to. |
| `identities` | `name TEXT PRIMARY KEY`, `initials TEXT`, `role TEXT`, `activity TEXT`, `score INTEGER`, `color TEXT`, `description TEXT` | Maps 1:1 to `Identity`; seed-only, never mutated by this feature. |
| `cloud_sources` | `name TEXT PRIMARY KEY`, `type TEXT`, `status TEXT`, `eventsToday INTEGER`, `health TEXT`, `icon TEXT`, `color TEXT`, `dataFreshnessMin INTEGER` | Maps 1:1 to `CloudSource`; seed-only. |
| `policies` | `title TEXT PRIMARY KEY`, `description TEXT`, `enabled INTEGER` (0/1), `category TEXT` | Maps 1:1 to `PolicyRule`; `enabled` mutated by the existing toggle endpoint (unchanged behavior, new storage). |
| `reports` | `title TEXT PRIMARY KEY`, `detail TEXT`, `period TEXT`, `type TEXT` | Maps 1:1 to `ReportTemplate`; seed-only. |
| `access_trend` | `label TEXT`, `events INTEGER`, `anomalies INTEGER` | Maps 1:1 to `AccessTrendPoint`; seed-only, read as an ordered list by rowid. |
| `service_risk` | `name TEXT`, `risk INTEGER`, `events INTEGER` | Maps 1:1 to `ServiceRisk`; seed-only. |
| `finding_explanations` | `finding_id TEXT PRIMARY KEY`, `explanation TEXT` | Maps 1:1 to the existing `finding_explanations` cache dict; unrelated to this feature's SQLite migration in behavior, just relocated storage. |

Single-row/singleton values (not lists) are stored as one row each in small
dedicated tables, read back into their existing Pydantic model on every
access — no change to their public shape:

| Table | Columns | Maps to |
|---|---|---|
| `model_rationale` | `top_finding_id TEXT`, `explanation TEXT`, `signals TEXT` (JSON array of `{label,score,tone}`) | `ModelRationale` |
| `service_risk_summary` | `highest_risk_service TEXT`, `sensitive_assets INTEGER`, `coverage TEXT` | `ServiceRiskSummary` |
| `configuration` | `notifications_enabled INTEGER`, `plain_language_explanations INTEGER` | `Configuration`; mutated by existing save endpoint |
| `meta` | `key TEXT PRIMARY KEY`, `value TEXT` | Holds `access_trend_peak_label`, `cloud_sources_online`, `average_review_time`, `signal_confidence_pct`, `identity_coverage_pct` — small seed scalars that don't warrant their own table |

`activity_source` (`Literal["seed","imported"]`, used by
`GET /api/activity`'s response) is also stored in `meta`, updated to
`"imported"` the first time `append_activity_events` successfully inserts
at least one row (existing semantics from `001`, unchanged: it's a flag
about whether *any* imported data is present, not a per-row attribution).

## Changed behavior 1: `activity_log` accepts appends, not replacement

**Before** (`001`): `Store.replace_activity_log(events, source)` — deletes
all prior rows, inserts `events`, sets `source`.

**After** (this feature): `Store.append_activity_events(events) -> int` —
inserts `events` as new rows (never deletes), returns the number inserted;
sets `meta.activity_source = "imported"` if not already. `GET /api/activity`
continues to return the full current table contents (now: seed rows + all
prior + current upload's rows) ordered by insertion (`id`) — no ordering
change from the caller's perspective beyond "more rows are now present."

**Validation** (unchanged from `001`): required fields `time`, `actor`,
`action`, `source`, `system`; `status`/`tone` default to
`"Normal"`/`"normal"` if absent. Max 10,000 records per *individual* upload
(unchanged cap — this is per-request, not a total-table cap; the table
itself has no size limit imposed by this feature).

## Changed behavior 2: `SummaryMetrics.activitiesChecked` is live

**Before** (`001`): `self._seed.activities_checked_base`, a constant read
once from the seed file's `summaryMetrics.activitiesChecked` and never
recomputed.

**After** (this feature): computed on every `compute_summary_metrics()`
call as `SELECT COUNT(*) FROM activity_log`, exactly mirroring how
`needsAttention`/`mostUrgentCase` in that same method are already derived
live from `findings` (per `001`'s data-model.md). At fresh startup, this
equals the seed file's `activityLog` array length (6, per the current
fixture) — **not** the seed file's separate `summaryMetrics.activitiesChecked`
value (1482), which was always a distinct "headline demo number" larger
than the literal seeded log. This is a deliberate, spec-required behavior
change (FR-009, spec SC-002): the KPI now reflects rows the system actually
holds, so it can visibly grow with uploads, at the cost of no longer
matching the original static demo figure at t=0. Documented as an
Assumption in spec.md; flagged again here since it's the one place a
number a user might have memorized (1482) will visibly change.

## Store shape (backend-internal, supersedes `001`'s "Store shape" section)

```text
Store (thin wrapper; all state now lives in SQLite, not Python attributes)
├── _conn: sqlite3.Connection            # single :memory: connection, opened once
├── get_findings() / get_finding(id) / update_finding_status(id, status) / add_finding(f)
├── compute_summary_metrics()            # activitiesChecked now: SELECT COUNT(*) FROM activity_log
├── get_activity_log() -> (events, source)
├── append_activity_events(events) -> int   # REPLACES replace_activity_log(events, source)
├── get_identities() / get_cloud_sources() / get_policies() / toggle_policy(title)
├── get_reports() / get_report(title)
├── get_configuration() / set_configuration(config)
└── get_finding_explanation(id) / cache_finding_explanation(id, text)
```

Every method's **signature and return type is unchanged** from `001` except
`replace_activity_log(events, source)` → `append_activity_events(events)`
(drops the `source` parameter — it's no longer meaningful to name a source
per-call since rows now accumulate from multiple sources within one run;
`meta.activity_source` is managed internally). `datasets.py` is the only
router file that needs a call-site change.
