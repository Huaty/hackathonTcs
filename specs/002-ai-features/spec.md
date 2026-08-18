# Feature Specification: AI-Assisted Investigation Features

**Feature Branch**: `002-ai-features`

**Created**: 2026-08-18

**Status**: Draft

**Input**: User description: "Add AI-powered features to Sentinel Access using liteLLM (model: claude-opus-4-6) as the LLM integration layer in the FastAPI backend. Three capabilities: (1) LLM-generated plain-language explanations for findings/evidence dossiers, replacing the static templated explanation text, generated on-demand and cached per finding in the in-memory store; (2) an "Ask Sentinel" natural-language copilot endpoint (POST /api/copilot/query) that lets an analyst ask questions in plain English about findings, activity, and identities, using LLM tool-calling to translate the question into filters over the existing in-memory store (no new data sources); (3) AI-drafted report narratives for the "Prepare report" action (daily summary, access activity export, identity review pack), replacing the static "prepared" stub with LLM-generated prose summarizing current findings/activity. All three call out to Claude via liteLLM (using ANTHROPIC_API_KEY from env, no new database, no auth), consistent with the project's existing no-DB/no-auth in-memory constitution. This depends on the existing 001-fastapi-backend-migration work (Store, routers, contracts) already being in place for command-center, activity, identities, estate, and is additive to the pending policies/reports/configuration work."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - AI-generated finding explanations (Priority: P1)

A security analyst opens the evidence dossier for a finding in the investigation queue and sees a plain-language explanation of why the finding was flagged, generated from that finding's actual evidence signals and baseline behavior, instead of a fixed templated sentence. Reopening the same finding later shows the same explanation without regenerating it.

**Why this priority**: This is the most visible, most on-brand upgrade — the product already markets itself around "explainable, prioritized security decisions," but today the explanation text is static. Making it genuinely generated from the finding's own evidence is the single highest-value change and touches the flagship Command Center view already in production.

**Independent Test**: Open several different findings' evidence dossiers and confirm each shows a distinct explanation that references that finding's own evidence signals (not a generic template); reopen the same finding twice and confirm the explanation text is identical both times (proving it's cached, not regenerated per view).

**Acceptance Scenarios**:

1. **Given** a finding with evidence signals and baseline behavior, **When** an analyst opens its evidence dossier for the first time, **Then** the explanation shown is generated from that finding's specific evidence rather than a fixed template string.
2. **Given** a finding whose explanation has already been generated once, **When** the analyst reopens its evidence dossier, **Then** the same explanation text is shown without a new generation delay.
3. **Given** the AI explanation service is unreachable or errors, **When** an analyst opens a finding's evidence dossier, **Then** a clear fallback explanation (e.g. the existing templated text) is shown instead of a blank or broken panel.

---

### User Story 2 - "Ask Sentinel" natural-language copilot (Priority: P1)

An analyst types a plain-English question — such as "show me high-risk findings on AWS IAM this week" or "which identities have unusual access right now" — into an "Ask Sentinel" input, and receives a direct answer along with the matching findings, activity events, or identities drawn from current data.

**Why this priority**: This is the most demoable and highest-differentiation feature — it turns the existing filterable tables into a conversational interface, and validates the "AI-assisted" positioning end-to-end. It's independently valuable even before the other two AI features exist.

**Independent Test**: Ask several different natural-language questions covering findings, activity, and identities, and confirm each returns a relevant answer plus the correct underlying records (verifiable by comparing against what the equivalent manual filter/search would return); ask a question with no matching data and confirm a clear "no results" answer rather than an error or fabricated data.

**Acceptance Scenarios**:

1. **Given** the analyst asks a question about findings (e.g. filtered by service, severity, or status), **When** the copilot answers, **Then** the answer is accompanied by the specific findings that match, sourced from current data.
2. **Given** the analyst asks a question about activity events or identities, **When** the copilot answers, **Then** the same pattern applies to those record types.
3. **Given** a question with no matching records, **When** the copilot answers, **Then** it clearly states no matches were found rather than inventing results.
4. **Given** the AI copilot service is unreachable or errors, **When** an analyst submits a question, **Then** a clear error message is shown and the analyst can still use the existing manual search/filter controls.

---

### User Story 3 - AI-drafted report narratives (Priority: P2)

An analyst clicks "Prepare report" on a report template (daily summary, access activity export, or identity review pack) and receives a generated narrative summarizing the current findings and activity relevant to that report, instead of a generic "report prepared" confirmation with no real content.

**Why this priority**: This raises the value of an existing but currently inert action. It's lower-frequency than the first two capabilities and depends on the reports feature already being wired to the backend, so it naturally follows the other two.

**Independent Test**: Prepare each of the three report templates and confirm the resulting narrative reflects the current state of findings/activity (e.g. changes when a new finding is simulated), rather than static boilerplate text.

**Acceptance Scenarios**:

1. **Given** the analyst prepares the daily summary report, **When** generation completes, **Then** the narrative reflects the current findings and activity, not a fixed stub message.
2. **Given** new findings or activity are added between two report preparations, **When** the analyst prepares the same report template again, **Then** the newly generated narrative reflects the updated data.
3. **Given** the AI report-drafting service is unreachable or errors, **When** an analyst prepares a report, **Then** a clear error is shown and the existing non-AI "prepared" confirmation still completes so the action doesn't appear to hang.

---

### Edge Cases

- What happens when the LLM service is slow to respond? The UI MUST show a clear loading/in-progress state for finding explanations, copilot answers, and report generation rather than appearing frozen.
- What happens when the LLM returns an implausible, empty, or malformed response? The system MUST fall back to a safe default (templated explanation, "unable to answer" copilot message, or the prior non-AI report stub) rather than displaying garbled or unfiltered output.
- What happens when an analyst asks the copilot something outside the product's data (e.g. general chit-chat or an unrelated question)? The copilot MUST decline gracefully and note it can only answer questions about the current security data, without fabricating findings.
- What happens when the underlying finding, activity, or identity data changes after a finding's explanation was cached (e.g. its status changes)? The cached explanation MAY become stale for narrative purposes but MUST NOT block or contradict the finding's current status shown elsewhere in the UI.
- How does the system handle a dataset import (replacing the active activity log) while previously generated finding explanations are cached? Cached explanations tied to findings that no longer exist or whose evidence changed MUST NOT be served for different underlying evidence.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST generate a plain-language explanation for a finding's evidence dossier from that finding's own evidence signals and baseline behavior, rather than from a fixed template.
- **FR-002**: The system MUST cache a generated finding explanation in server-side in-memory state so repeated views of the same finding do not trigger repeated generation, for as long as the backend process runs.
- **FR-003**: The system MUST expose a way for an analyst to submit a plain-English question and receive an answer accompanied by the specific matching findings, activity events, or identities from current data.
- **FR-004**: The copilot MUST only surface records that actually exist in current data — it MUST NOT fabricate findings, activity, or identities in its answer.
- **FR-005**: The copilot MUST respond clearly when no data matches a question, and MUST decline gracefully when asked something unrelated to the product's security data.
- **FR-006**: The system MUST generate a narrative summary of current findings/activity when an analyst prepares a report (daily summary, access activity export, identity review pack), reflecting the data active at generation time.
- **FR-007**: All three AI capabilities MUST degrade to a clear, non-broken fallback (existing templated explanation, an "unable to answer" copilot message, or the prior non-AI "prepared" confirmation) when the underlying AI service is unreachable, errors, or times out.
- **FR-008**: The system MUST show a clear in-progress/loading indication for each AI-backed action (explanation generation, copilot query, report generation) rather than leaving the UI in an ambiguous state while waiting.
- **FR-009**: These AI features MUST NOT require any new persistent datastore or authentication mechanism, consistent with the product's existing no-database, no-auth, in-memory-only posture.
- **FR-010**: The AI features MUST operate only on data already present in the system's existing in-memory state (findings, activity log, identities) — no new external data sources are introduced.

### Key Entities

- **Finding Explanation**: The generated plain-language narrative attached to a Finding, derived from its evidence signals and baseline behavior; cached once generated per finding.
- **Copilot Query**: An analyst's natural-language question and the corresponding answer, including the set of Findings, Activity Events, and/or Identities returned as supporting evidence for that answer.
- **Report Narrative**: The generated prose summary attached to a prepared Report, reflecting the Findings and Activity Events active at the time of preparation.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: An analyst opening any finding's evidence dossier sees an explanation that is specific to that finding's evidence (not identical boilerplate text across unrelated findings).
- **SC-002**: Reopening a previously viewed finding shows its explanation without a new noticeable generation delay, distinguishing a first view from a repeat view.
- **SC-003**: An analyst can get a relevant, data-backed answer to a natural-language question about findings, activity, or identities without needing to know the manual filter/search controls.
- **SC-004**: When the AI backend is unreachable, all three AI-backed actions (finding explanation, copilot query, report preparation) still leave the analyst with a usable, non-broken experience rather than a stuck or blank UI.
- **SC-005**: A report narrative generated after new findings appear differs from one generated before those findings existed, demonstrating the narrative reflects live data rather than being static.

## Assumptions

- LLM access is provided via a self-hosted **liteLLM proxy server** (OpenAI-compatible `POST /v1/chat/completions` endpoint, e.g. `http://localhost:4000`), not the liteLLM Python library called in-process. The FastAPI backend calls this proxy over HTTP, authenticated with a proxy virtual key (`Authorization: Bearer <key>`), requesting the `claude-opus-4-6` model alias as configured on the proxy. The proxy itself holds the real `ANTHROPIC_API_KEY` and is run/configured as a separate process alongside the FastAPI backend — no new secrets-management infrastructure beyond existing environment-variable configuration, but this is an added deployable component beyond the FastAPI app itself (a deliberate, explicit exception to Principle III's "no external services," justified by the desire to keep the AI provider swappable/proxyable without changing backend code).
- Persistence for AI-generated content (cached finding explanations) is in-memory only, on the same `Store` object established by the 001 FastAPI backend migration, and is lost on backend restart along with all other in-memory state — consistent with the project's constitution (Principle III: Simplicity and YAGNI).
- No authentication or authorization is added for the AI endpoints, matching the product's existing no-auth demo posture (Principle III).
- This feature depends on the 001-fastapi-backend-migration work being in place — specifically the `Store`, the command-center/activity/identities/estate routers, and (for the report-narrative capability) the reports router from that migration's User Story 3.
- The copilot's "tool-calling to translate questions into filters" is scoped to read-only queries over existing in-memory data (findings, activity, identities) — it does not perform write actions (e.g. it cannot start an investigation or escalate a finding on the analyst's behalf) as part of this feature.
- Report narratives are prose summaries only; this feature does not add real file generation, export formats, or external case-management integration beyond what already exists.
- "Prepare report" and finding-explanation generation remain demo-style AI features appropriate to synthetic/demo data, consistent with the product's existing demo-safety posture (Principle V).
