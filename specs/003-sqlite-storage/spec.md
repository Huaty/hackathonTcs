# Feature Specification: SQLite In-Memory Storage & Additive Dataset Uploads

**Feature Branch**: `003-sqlite-storage`

**Created**: 2026-08-18

**Status**: Draft

**Input**: User description: "Replace the in-memory Python object Store with a SQLite (in-memory) database as the backend's persistence layer for all entities, seeded on startup from server/data/synthetic-data.json (source of truth). Change dataset upload (POST /api/datasets) so a newly uploaded JSON file's activity records are appended to the existing activity log instead of replacing it, so total activity count strictly increases with every successful upload. Make summaryMetrics.activitiesChecked a live count of stored activity rows instead of a static seed value."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Backend state survives a rewrite of its storage engine unchanged (Priority: P1)

As the operator of the Sentinel Access demo, when the backend starts up it loads `server/data/synthetic-data.json` into a SQLite (in-memory) database instead of a plain Python object store, and every existing screen (Command Center, Activity Explorer, Identity Profiles, Cloud Estate, Policies, Reports, Configuration) continues to show exactly the same data and behave exactly the same way as before.

**Why this priority**: This is the foundation — every other story depends on the storage engine swap being behavior-preserving. If any existing endpoint's response shape or values change, it breaks the frontend and violates the "backend-swap, not a redesign" principle already established for this project.

**Independent Test**: Start the backend fresh (no uploads yet), call every existing `/api/*` endpoint, and diff the response bodies against the pre-migration (in-memory object store) responses for the same seed file — they must be identical in shape and values.

**Acceptance Scenarios**:

1. **Given** a freshly started backend, **When** any read endpoint (findings, identities, cloud estate, policies, reports, configuration, activity log, command center summary) is called, **Then** the response matches the values in `server/data/synthetic-data.json` exactly as it did before the storage change.
2. **Given** a freshly started backend, **When** a finding's status is updated (start investigation / escalate), **Then** the change is reflected immediately in subsequent reads of that finding and in the derived `needsAttention` / `mostUrgentCase` KPIs, the same as before.
3. **Given** a freshly started backend, **When** a policy is toggled or configuration is saved, **Then** the change persists for the remainder of that server run and is reflected on the next read.

---

### User Story 2 - Uploading a dataset adds to the activity history instead of replacing it (Priority: P1)

As an analyst reviewing activity, when I upload a new JSON (or CSV) activity dataset — including files that use a different field-naming convention than the seed data, such as `datasets/synthetic-data.json` (`timestamp`/`user`/`action`/`sourceIp`/`service`/`status`) — the newly parsed records are added to the existing activity log rather than replacing what was already there, so nothing I previously saw disappears and the total number of tracked activities goes up.

**Why this priority**: This is the specific behavior change the user asked for and the main reason for this feature; it's independently valuable even before any KPI changes.

**Independent Test**: Note the current activity log row count, upload a valid dataset file with N accepted records, and confirm the log now shows (previous count + N) rows, with the previously-existing rows still present and unchanged.

**Acceptance Scenarios**:

1. **Given** an activity log with existing rows (seed or prior uploads), **When** a valid dataset file with N acceptable records is uploaded, **Then** the activity log afterward contains all prior rows plus N new rows, in total.
2. **Given** a dataset file using the alternate flat schema (`timestamp`, `user`, `action`, `sourceIp`, `service`, `status`), **When** it is uploaded, **Then** its records are normalized into the same activity event shape as seed/CSV imports and appended (not replacing) the log.
3. **Given** two sequential valid uploads in the same server run, **When** both complete, **Then** the activity log reflects records from both uploads plus the original seed data, and the import result response reports the count accepted from that specific upload (not the cumulative total).
4. **Given** an uploaded file that is malformed or contains zero usable records, **When** the upload is submitted, **Then** the existing activity log is left completely unchanged and an error/result is returned describing the problem.

---

### User Story 3 - The "activities checked" number reflects everything the system has actually seen (Priority: P2)

As a user of the Command Center, the "activities checked" KPI number should go up when I upload a new dataset, so the headline metric visibly reflects the growing activity history rather than staying frozen at a demo constant.

**Why this priority**: Builds on Story 2 — once activity rows can grow, the KPI that's supposed to summarize "how much have we checked" should stay truthful. It's lower priority than the storage swap and append behavior themselves because it's a single derived-value change, not a structural one.

**Independent Test**: Read the Command Center summary metrics, upload a dataset with N new records, re-read the summary metrics, and confirm `activitiesChecked` increased by exactly N.

**Acceptance Scenarios**:

1. **Given** a freshly started backend, **When** the Command Center summary is read, **Then** `activitiesChecked` equals the number of rows currently in the activity log (seed count).
2. **Given** a successful dataset upload accepting N records, **When** the Command Center summary is read again, **Then** `activitiesChecked` equals its prior value plus N.
3. **Given** a rejected/failed upload (zero records accepted), **When** the Command Center summary is read again, **Then** `activitiesChecked` is unchanged.

### Edge Cases

- What happens when an uploaded file's records fully overlap with data already in the log (identical timestamp/actor/action)? → They are still appended as separate rows in this feature (no de-duplication); the log and `activitiesChecked` grow by the accepted count regardless of similarity to existing rows.
- What happens when a dataset is uploaded before any prior upload in the same run? → It appends on top of the seed-loaded rows, not an empty log.
- What happens when the backend restarts? → The SQLite database is in-memory and is rebuilt from `server/data/synthetic-data.json` on the next startup; all prior uploads in earlier runs are lost, matching today's existing restart behavior (seed-only state resets on restart already).
- What happens when the upload exceeds the existing 10,000-record file limit? → Same as today: the whole file is rejected with an error and nothing is appended.
- What happens to `mostUrgentCase` / `needsAttention` on upload? → Unaffected by this feature; those remain derived from `findings`, not from the activity log, and findings are not created by dataset upload.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: On backend startup, the system MUST populate its storage entirely from `server/data/synthetic-data.json`, and this file remains the single source of truth for initial state — no other seed source may be introduced.
- **FR-002**: Every entity currently held in the in-memory object store (findings, model rationale, access trend, service risk, activity log, identities, cloud sources, policies, reports, configuration) MUST be persisted in the new storage layer, not partially migrated.
- **FR-003**: All existing read endpoints MUST return data identical in shape and value to today's behavior immediately after a fresh startup (before any mutation or upload), for the same seed file.
- **FR-004**: All existing mutation endpoints (finding status update, policy toggle, configuration save, report preparation, dataset import) MUST continue to work with the same request/response contracts as today.
- **FR-005**: Dataset upload (JSON or CSV) MUST append newly parsed, valid activity records to the existing activity log rather than replacing it.
- **FR-006**: Dataset upload MUST continue to accept files using the existing flexible field-alias matching (including the alternate flat schema exemplified by `timestamp`/`user`/`action`/`sourceIp`/`service`/`status`), normalizing accepted records into the same activity event shape used elsewhere in the system.
- **FR-007**: If a dataset upload contains zero usable records or fails validation (invalid JSON/CSV, exceeds the record limit), the activity log MUST remain unchanged — partial or failed uploads must not partially append.
- **FR-008**: The dataset import result returned to the caller MUST report the accepted/rejected counts for that specific upload, not the cumulative log size.
- **FR-009**: `summaryMetrics.activitiesChecked` MUST be computed as the current count of rows in the activity log at read time, rather than a fixed seed constant.
- **FR-010**: A dataset upload MUST NOT create, modify, or remove `Finding` records, identities, policies, cloud sources, or reports — its effect is scoped to the activity log (and the derived `activitiesChecked` metric) only.
- **FR-011**: Existing derived/computed values that are not activity-log-based (`needsAttention`, `mostUrgentCase`) MUST remain unaffected by dataset uploads, continuing to derive solely from `findings`.
- **FR-012**: The storage layer MUST remain single-process, in-memory for the lifetime of one server run (matching today's restart-resets-state behavior) — no requirement to persist across restarts or to an external database service.

### Key Entities

- **ActivityEvent**: A single normalized activity log row (`time`, `actor`, `action`, `source`, `system`, `status`, `tone`). Grows over the life of a server run via seed load plus zero or more appended dataset uploads; never wholesale-replaced by this feature.
- **Finding (Alert)**: Unchanged in this feature — investigation-queue item with mutable `status`; not affected by dataset upload.
- **SummaryMetrics**: Computed KPI view; `activitiesChecked` becomes a live count of `ActivityEvent` rows (was a static seed number), all other fields unchanged.
- **Identity, CloudSource, PolicyRule, ReportTemplate, Configuration, ModelRationale, AccessTrendPoint, ServiceRisk**: Unchanged shapes; migrated to the new storage layer as-is, values sourced from the same seed file.
- **DatasetImportResult**: Unchanged shape (`acceptedCount`, `rejectedCount`, `errors`) — still describes the outcome of one specific upload, not the resulting total log size.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Immediately after a fresh backend start, 100% of existing screens/endpoints show values identical to the pre-migration behavior for the same seed file (zero regressions).
- **SC-002**: After any single successful dataset upload that accepts N records, the activity log total and the `activitiesChecked` KPI each increase by exactly N, verified across at least 3 consecutive uploads in the same run (i.e., totals accumulate correctly, not just after one upload).
- **SC-003**: A failed or zero-record upload changes neither the activity log count nor `activitiesChecked` — verified with at least one malformed-file test.
- **SC-004**: Previously visible activity rows remain visible and unchanged after any number of subsequent uploads in the same run (no data loss on append).
- **SC-005**: All previously passing backend contract/integration tests continue to pass unmodified in their expected outcomes after the storage engine swap (test code may be adapted to the new storage internals, but observable API behavior must not change) except where this feature explicitly changes behavior (append-not-replace, live `activitiesChecked`).

## Assumptions

- "SQLite in-memory" means a single in-process SQLite database (e.g. Python's built-in `sqlite3` connected to `:memory:`) that lives for the duration of one backend server run — not a file on disk and not a separately-hosted database service. This is treated as a storage-implementation change, not the introduction of "external" infrastructure in the sense the project's existing simplicity principle is guarding against; the plan for this feature must explicitly justify this reading.
- No de-duplication of activity records across uploads is required for this feature; re-uploading the same file twice will append the same records twice, and the count will grow by the full accepted count both times. Only the "no duplicate handling" default is assumed here — a future feature could add de-duplication if desired.
- The `datasets/synthetic-data.json` file used for testing this feature contains records in the alternate flat schema (not the seed file's rich `alerts`/`identities` structure) and is expected to go through the same field-alias normalization path that CSV/JSON imports already use today, becoming `ActivityEvent` rows.
- `activitiesChecked` becoming a live count is the only KPI semantic change in this feature; `needsAttention`, `mostUrgentCase`, `signalConfidencePct`, `identityCoveragePct`, and `averageReviewTime` are out of scope and keep their current (seed-derived or otherwise static) values.
- Concurrent uploads racing each other are out of scope; the demo is single-user/single-process and this feature does not add locking/transaction requirements beyond whatever SQLite provides by default.
