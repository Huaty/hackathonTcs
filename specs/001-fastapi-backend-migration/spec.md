# Feature Specification: FastAPI Backend Migration

**Feature Branch**: `001-fastapi-backend-migration`

**Created**: 2026-08-18

**Status**: Draft

**Input**: User description: "Sentinel Access currently ships as a fully static, browser-only demo — all data for the Command Center, Activity Explorer, Identity Profiles, Cloud Estate, Policies, Reports, and Configuration views is hardcoded in the frontend. Replace this with a real Python FastAPI backend that serves the same data and supports the same interactive actions (starting an investigation, escalating, toggling policies, preparing reports, saving settings, importing a dataset, simulating an anomaly), so the frontend reads and writes through a live API instead of local fixtures. Persistence is in-memory/JSON-seeded (no database), and there is no authentication."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Command Center runs on live data (Priority: P1)

A security analyst opens the Command Center and sees the KPI banner, behavioral-variance chart, service-risk chart, and investigation queue populated by a live backend service instead of hardcoded values. Clicking a queue row opens the evidence dossier with data from the same service. Starting an investigation or escalating a finding updates its status via the backend and that change is reflected back in the queue.

**Why this priority**: This is the flagship view and the most visible proof that the product is no longer a static mock. It also exercises both read (KPIs, queue, dossier) and write (status change) paths, which every other view depends on the same pattern to follow.

**Independent Test**: Start the backend and frontend together, load the Command Center, and confirm KPI numbers and queue rows match the backend's current state (not the old hardcoded values). Click "Start investigation" on a finding and confirm its status changes to "In progress" both in the UI and on a subsequent full page reload (proving the change was persisted server-side, not just in local React state).

**Acceptance Scenarios**:

1. **Given** the backend is running with its seeded dataset, **When** an analyst loads the Command Center, **Then** the KPI banner, queue, and charts show values sourced from the backend response, not hardcoded frontend constants.
2. **Given** a finding in the investigation queue, **When** the analyst clicks "Start investigation" and confirms, **Then** the finding's status updates to "In progress," the dossier closes, and reloading the page still shows the updated status.
3. **Given** a finding in the investigation queue, **When** the analyst escalates it, **Then** the escalation is recorded by the backend and reflected in the queue's visible state.
4. **Given** the analyst clicks "Simulate anomaly," **When** the request completes, **Then** a new synthetic high-severity finding appears in the queue sourced from the backend (not injected purely client-side).

---

### User Story 2 - Explorer, Identity, and Estate views run on live data (Priority: P2)

An analyst browses the Activity Explorer, Identity Profiles, and Cloud Estate views and sees searchable/filterable data, identity risk cards, and connected-source health information sourced from the backend rather than hardcoded arrays.

**Why this priority**: These are the secondary investigation surfaces analysts use after the Command Center; they share the same underlying entities (activity events, identities) as User Story 1 and should reflect the same live backend state, but they are not required for a minimal usable demo the way the Command Center is.

**Independent Test**: Load each of the three views independently and confirm their content matches backend-served data; verify that a status change made in one view (e.g., an investigation started on the Command Center) is visible where relevant in Activity Explorer without a code change or manual refresh of fixtures.

**Acceptance Scenarios**:

1. **Given** the backend is running, **When** an analyst opens Activity Explorer, **Then** the event list, "Needs attention" / "Normal" grouping, and search/filter results are computed from backend data.
2. **Given** the backend is running, **When** an analyst opens Identity Profiles, **Then** identity cards, risk scores, and activity timelines are sourced from the backend.
3. **Given** the backend is running, **When** an analyst opens Cloud Estate, **Then** connected-source status, event volume, and health indicators are sourced from the backend.

---

### User Story 3 - Policies, Reports, and Configuration act through the backend (Priority: P3)

An analyst toggles a detection policy, prepares a report, or saves configuration preferences, and these actions are persisted by the backend rather than only updating local component state.

**Why this priority**: These views are lower-frequency, administrative actions. They complete the migration but are not required to demonstrate the core investigative workflow.

**Independent Test**: Toggle a policy off/on, prepare a report, and save a settings change; reload the page and confirm each change persisted (fetched fresh from the backend) rather than reverting to defaults.

**Acceptance Scenarios**:

1. **Given** a list of detection policies, **When** an analyst toggles one off, **Then** the backend records the new state and it remains off after a page reload.
2. **Given** a report template, **When** an analyst clicks "Prepare report," **Then** the backend processes the request and the UI confirms completion using the backend's response.
3. **Given** notification/plain-language preference toggles, **When** an analyst saves preferences, **Then** the backend stores the updated preferences and they are reflected on next load.

---

### User Story 4 - Dataset import is handled by the backend (Priority: P3)

An analyst uploads a CSV/JSON dataset of access activity, and the backend validates, ingests, and stores it in place of (or alongside) the seeded demo data, so Activity Explorer and related views reflect the imported data for the running backend session.

**Why this priority**: This upgrades an existing but explicitly browser-only, session-scoped feature; it depends on the entities already served by User Stories 1-2, so it is sequenced after them.

**Independent Test**: Upload a valid CSV file, confirm the backend reports a validated record count, and confirm Activity Explorer subsequently reflects the imported records; upload an invalid file and confirm the backend returns a clear validation error without corrupting existing state.

**Acceptance Scenarios**:

1. **Given** a valid CSV or JSON dataset under the existing size cap, **When** an analyst uploads it, **Then** the backend validates and ingests the records and returns a summary (accepted/rejected counts).
2. **Given** an invalid or malformed file, **When** an analyst uploads it, **Then** the backend rejects it with a clear error and existing data is unaffected.
3. **Given** a dataset has been imported, **When** an analyst views Activity Explorer, **Then** the imported records are what is displayed, matching the current "imported data replaces synthetic data for the session" behavior.

---

### Edge Cases

- What happens when the backend has just started and no dataset has been imported? The seeded synthetic dataset (derived from `server/data/synthetic-data.json`) MUST be served as the default state.
- What happens when the backend process restarts? In-memory state (status changes, imported datasets, policy toggles, saved settings) resets to the seeded defaults, since there is no database — this is expected behavior for this feature's scope.
- How does the system handle a dataset upload that exceeds the existing 10,000-record cap? The backend MUST reject or truncate consistently with a clear message, matching current client-side behavior.
- How does the system handle the frontend requesting data while the backend is unreachable? The UI MUST show a clear error/loading state rather than silently falling back to stale hardcoded values.
- What happens if two analysts (two browser sessions) act concurrently (e.g., both escalate the same finding)? The backend MUST apply a consistent last-write-wins result and both sessions MUST be able to observe the resulting state on next fetch.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The backend MUST expose an endpoint that returns Command Center data: summary KPIs (activities checked, needs-attention count, most urgent case, average review time, signal confidence, identity coverage), the investigation queue, and chart data (behavioral-variance over time, service-risk breakdown).
- **FR-002**: The backend MUST expose an endpoint that returns full evidence-dossier detail for a single finding (explanation, evidence signals, baseline, recommended action, current status).
- **FR-003**: The backend MUST support updating a finding's status (e.g., to "In progress" on investigation start, or "Escalated") and persist that change in its in-memory state for subsequent reads.
- **FR-004**: The backend MUST support injecting a synthetic high-severity finding into the queue on request (backing the "Simulate anomaly" action).
- **FR-005**: The backend MUST expose an endpoint that returns Activity Explorer data (access events with plain-language explanations, "Needs attention"/"Normal" classification) reflecting the currently active dataset (seeded or imported).
- **FR-006**: The backend MUST expose an endpoint that returns Identity Profiles data (identity list with risk scores, behavior summary, activity timeline per identity).
- **FR-007**: The backend MUST expose an endpoint that returns Cloud Estate data (connected sources, connection status, event volume, health).
- **FR-008**: The backend MUST expose endpoints to list detection policies and toggle a policy's enabled state, persisting the change.
- **FR-009**: The backend MUST expose endpoints to list report templates and to "prepare" a report, returning a completion result.
- **FR-010**: The backend MUST expose endpoints to read and save configuration/settings preferences (notification and plain-language-explanation toggles).
- **FR-011**: The backend MUST expose an endpoint that accepts a CSV or JSON dataset upload, validates it against the existing format/size rules, ingests valid records into in-memory state, and returns a summary of accepted/rejected records.
- **FR-012**: The backend MUST seed its initial in-memory state from the existing synthetic dataset shape (`server/data/synthetic-data.json`) so first-run behavior matches today's demo content.
- **FR-013**: The frontend MUST be updated so each of the six views (Command Center, Activity Explorer, Identity Profiles, Cloud Estate, Policies, Reports/Configuration) reads its data from the corresponding backend endpoint instead of hardcoded local constants.
- **FR-014**: The frontend MUST route the interactive actions (start investigation, escalate, simulate anomaly, toggle policy, prepare report, save settings, import dataset) through the backend instead of only mutating local component state.
- **FR-015**: The system MUST NOT require authentication to access any endpoint (matching current no-auth demo posture).
- **FR-016**: The backend MUST return clear, distinguishable error responses for invalid requests (e.g., unknown finding ID, malformed dataset upload) so the frontend can present a meaningful message instead of failing silently.

### Key Entities

- **Finding / Alert**: A detected access-activity event under review — severity, entity (user/service identity), source, region, service, risk score, description, evidence signals, baseline behavior, recommended action, and current status (open/in-progress/escalated).
- **Identity**: A user or service identity — role, risk score, "what looks unusual" vs. "what is normally expected" summary, and an activity timeline.
- **Activity Event**: A single access-activity record shown in Activity Explorer — attributes needed for search/filter and plain-language explanation, plus attention classification.
- **Cloud Source**: A connected cloud/identity source (e.g., AWS IAM, Azure AD) — connection status, event volume, health.
- **Policy Rule**: A detection rule with a name/description and an enabled/disabled state.
- **Report Template**: A report definition (e.g., daily summary, access activity export, identity review pack) and its "prepared" outcome.
- **Configuration / Settings**: Notification and plain-language-explanation preference values.
- **Dataset Import Result**: The outcome of an uploaded dataset — accepted/rejected record counts and validation messages.
- **Summary Metrics (KPIs)**: Aggregate Command Center figures — activities checked, needs-attention count, most urgent case, average review time, signal confidence, identity coverage.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All six dashboard views (Command Center, Activity Explorer, Identity Profiles, Cloud Estate, Policies, Reports/Configuration) display data that changes when the backend's underlying data changes, with zero views still driven by hardcoded frontend constants.
- **SC-002**: A status change made to a finding (start investigation / escalate) survives a full page reload, proving the change was persisted server-side rather than only in local UI state.
- **SC-003**: An analyst can upload a dataset and see Activity Explorer reflect the imported records within the same interaction flow that exists today, with validation feedback shown for invalid files.
- **SC-004**: When the backend is stopped or unreachable, every view shows a clear loading/error indication instead of blank content or stale hardcoded data.
- **SC-005**: The `needsAttention` count and `mostUrgentCase` KPI are always internally consistent with the visible investigation queue — `needsAttention` equals the number of findings not yet escalated, and `mostUrgentCase` names the highest-scoring finding among them. This may differ from the original static demo's hardcoded figures (which were not derived from the queue); consistency with the live queue takes priority over matching the old demo's numbers.

## Assumptions

- Persistence is in-memory, seeded from `server/data/synthetic-data.json` at backend startup; there is no database and no requirement for data to survive a backend restart (per project constitution, Principle III).
- No authentication or authorization is required for any endpoint (per project constitution, Principle III).
- The backend is a new standalone FastAPI service; whether it replaces or runs alongside the existing Express static-file server (`server/index.ts`) is a technical decision to be made at planning time, not a scoping decision for this spec.
- The existing 10,000-record dataset-import cap and CSV/JSON format expectations carry over unchanged from the current client-side implementation.
- "Prepare report" and "simulate anomaly" remain demo-style actions (no real file generation or external case-management integration), consistent with `todo.md`'s note that real case-management integration is deferred until a backend is available — this feature provides that backend foundation but does not itself implement external integrations.
- Existing visual design, component structure, and interaction timing (animations, toasts) are unchanged; only the data source and persistence of actions change.
