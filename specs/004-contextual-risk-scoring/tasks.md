---
description: "Revised implementation tasks for deterministic policy scoring plus bounded AI context"
---

# Tasks: Policy-First AI Contextual Risk Scoring

**Input**: Revised documents in `/specs/004-contextual-risk-scoring/`

**Prerequisites**: `spec.md`, `plan.md`, `research.md`, `data-model.md`, `contracts/`, `quickstart.md`

**Tests**: Required by SC-001–SC-008. Policy arithmetic, AI validation/fallback, floors, identity linkage, policy history, and synthetic oracle tests are implementation gates.

**Important revision**: Prior partial code implementing Isolation Forest plus weighted context is superseded. Stable identity/event/baseline work may be retained after review; anomaly-score fields/formulas/tests must not remain in the completed feature.

## Format

`[ID] [P?] [Story] Description`

- `[P]` may run in parallel after dependencies because files/concerns differ.
- Story labels map to revised `spec.md` User Stories 1–5.
- Paths are repository-relative.

---

## Phase 1: Reconcile the Superseded Partial Implementation

**Purpose**: Establish a coherent starting point before adding revised behavior.

- [ ] T001 Audit the current dirty worktree against revised `data-model.md`; document in the implementation handoff which stable identity/event/baseline changes are retained and which Isolation Forest/weighted-context changes are removed, without reverting unrelated user work.
- [ ] T002 Remove superseded Isolation Forest request/response/schema/database fields and weighted `securityContextScore` arithmetic from `sentinel-access/backend/app/schemas/entities.py`, `app/db.py`, `app/services/risk_scoring.py`, and partial tests; retain normalized identities/events/baselines that satisfy revised FR-001–FR-004.
- [ ] T003 Replace service provenance constants in `sentinel-access/backend/app/services/__init__.py` with `BASELINE_VERSION`, `POLICY_VERSION = "policy-catalog-v1"`, `PROMPT_VERSION = "risk-context-prompt-v1"`, and `SCORING_VERSION = "policy-ai-risk-v1"`.
- [ ] T004 Run the existing backend contract/integration suite with the project `.venv`; resolve reconciliation regressions while preserving existing AI, report, dataset, finding, and profile behavior.

**Checkpoint**: No revised runtime API or test expects an Isolation Forest score; existing behavior remains green.

---

## Phase 2: Foundational Policy and Persistence Model (Blocking)

**Purpose**: Add safe versioned policies, immutable evaluations, bounded AI decisions, and final assessments.

- [ ] T005 [P] Define strict Pydantic enums/models for `PolicyRule`, `PolicyRuleResult`, `PolicySnapshot`, `PolicyEvaluation`, `AIContextResponse`, `AIContextDecision`, `RiskCalculation`, and revised `RiskAssessment` in `sentinel-access/backend/app/schemas/entities.py`; allowed adjustments are exactly `-15,-5,0,10,20,25`.
- [ ] T006 Evolve `sentinel-access/backend/app/db.py`: extend `policies` with `rule_id`, `condition_key`, `points`, `severity_floor`, `policy_version`, `updated_at`; add `policy_evaluations`, `ai_context_decisions`, and revised `risk_assessments` exactly as `data-model.md`; retain atomic transaction/thread locking.
- [ ] T007 Replace scoring-policy seeds in `sentinel-access/server/data/synthetic-data.json` with every Policy Catalog v1 rule and update `sentinel-access/backend/app/seed_data.py` to seed stable IDs, condition keys, points, floors, enabled state, and version while preserving existing policy UI fields.
- [ ] T008 Extend `sentinel-access/backend/app/store.py` with row mappers and CRUD for versioned policy snapshots, immutable rule results/evaluations, AI decisions, and revised assessments; no read reconstructs historical results from current policy rows.
- [ ] T009 Add/update storage parity tests in `sentinel-access/backend/tests/integration/test_storage_parity.py` for the evolved policy response and prove existing configuration/finding/report mutations still persist.

**Checkpoint**: Policy Catalog v1 and immutable result storage exist; all prior APIs still operate.

---

## Phase 3: User Story 1 - Explainable Policy-First Score (Priority: P1) 🎯 MVP

**Goal**: Evaluate every approved rule, calculate the capped policy score and strongest floor, and return a complete assessment even with AI adjustment zero.

**Independent Test**: Evaluate normal, individual-rule, overlap, cap, disabled, unknown-baseline, High-floor, Critical-floor, and severity-boundary fixtures without a live AI proxy.

### Tests

- [ ] T010 [P] [US1] Create `sentinel-access/backend/tests/unit/test_policy_engine.py` covering every Policy Catalog v1 condition, all-context additive behavior, highest-action selection, highest-compound/sequence selection, matched-but-unselected visibility, disabled rules, unknown baseline, cap 100, and strongest floor.
- [ ] T011 [P] [US1] Revise `sentinel-access/backend/tests/unit/test_baseline.py` to assert 30-day/15-minute/p95/20-events-over-7-days behavior and provide explicit facts consumed by policy conditions rather than a weighted baseline-deviation score.
- [ ] T012 [P] [US1] Revise `sentinel-access/backend/tests/unit/test_risk_scoring.py` for `clamp(policyScore + aiAdjustmentApplied)` followed by floor 0/65/85 and final severity boundaries 39/40, 64/65, 84/85; delete former weighted/rounding tests.

### Implementation

- [ ] T013 [US1] Reconcile/complete `sentinel-access/backend/app/services/baseline.py` so it returns versioned baseline facts and `matched/not_matched/unknown` evidence used by `POL-NEW-SOURCE`, `POL-UNUSUAL-TIME`, `POL-NEW-SERVICE-ACTION`, and `POL-HIGH-FREQUENCY`. (Depends on T011.)
- [ ] T014 [US1] Create `sentinel-access/backend/app/services/policy_engine.py` with approved `condition_key` implementations for all catalog rules, including bounded same-identity/session 60-minute sequences; never execute database-provided expressions. (Depends on T005, T007, T010, T013.)
- [ ] T015 [US1] Implement policy grouping/selection, full result evidence, capped `policyScore`, policy snapshot hash/version, and strongest floor in `policy_engine.py`. (Depends on T014.)
- [ ] T016 [US1] Rewrite `sentinel-access/backend/app/services/risk_scoring.py` as the pure revised calculator accepting policy score, applied adjustment, and floor minimum; it owns clamp, post-AI floor, score, and severity only. (Depends on T012.)
- [ ] T017 [US1] Add policy snapshot/evaluation orchestration and persistence to `sentinel-access/backend/app/store.py`, selecting exact event/baseline/correlated sequence and returning immutable evaluations. (Depends on T008, T013–T015.)
- [ ] T018 [US1] Create/revise `sentinel-access/backend/app/routers/risk_assessments.py` so `POST /api/risk-assessments` can complete policy-only with an explicit zero AI fallback, and implement immutable GET endpoints from `contracts/risk-assessments.md`.
- [ ] T019 [US1] Add `sentinel-access/backend/tests/contract/test_risk_assessments.py` for policy result shape, policy-only fallback, idempotent 200/201 behavior, event 404, prerequisite 409, arithmetic, floors, and evidence/version fields.
- [ ] T020 [US1] Run T010–T012, T019, and existing contract tests; satisfy SC-001/SC-003 before implementing live AI adjustment.

**Checkpoint**: A fully usable, explainable policy-only risk assessment is the MVP; AI cannot block it.

---

## Phase 4: User Story 2 - Bounded AI Context and Safe Degradation (Priority: P1)

**Goal**: Add prompt-driven context with strict adjustment/confidence/evidence/mitigation validation and zero adjustment for every unsafe path.

**Independent Test**: Mock every adjustment and failure path; verify policies and floors are immutable and only validated context changes the pre-floor score.

### Tests

- [ ] T021 [P] [US2] Create `sentinel-access/backend/tests/unit/test_ai_risk_context.py` for all allowed adjustments, unsupported values, confidence 0.59/0.60, evidence-ID validation, positive-without-evidence, negative-without-mitigation, malformed/empty responses, and prompt-like raw event strings.
- [ ] T022 [P] [US2] Create `sentinel-access/backend/tests/integration/test_ai_risk_fallback.py` covering timeout/network failure, invalid response, low confidence, valid positive/negative adjustment, cache hit, forced refresh, and proof that AI cannot change policy results/floors/arithmetic.

### Implementation

- [ ] T023 [US2] Create `sentinel-access/backend/app/services/ai_risk_context.py` with a fixed prompt rubric, explicit untrusted-data delimiters, identity/baseline/policy summary, and at most 20 same-identity/session events from the prior 60 minutes. (Depends on T005, T021.)
- [ ] T024 [US2] Extend `sentinel-access/backend/app/ai_client.py` with a structured risk-context call using the existing liteLLM configuration and 15-second timeout; transport/shape errors raise `AIServiceError` and never fail policy evaluation.
- [ ] T025 [US2] Implement AI response validation/application in `ai_risk_context.py`, recording raw/applied adjustment, status, validation errors, evidence, confidence, model, and prompt version; every invalid/unavailable path applies zero. (Depends on T021, T023, T024.)
- [ ] T026 [US2] Add AI decision cache/upsert and force-refresh versioning to `sentinel-access/backend/app/store.py` using event, baseline, policy snapshot, prompt version, and model; never overwrite prior decisions. (Depends on T008, T025.)
- [ ] T027 [US2] Integrate T025–T026 with risk-assessment orchestration and revised `risk_scoring.py`, applying policy floors after AI and persisting the full response from `contracts/risk-assessments.md`.
- [ ] T028 [US2] Run T021–T022 plus existing copilot/explanation/report AI tests; satisfy SC-002–SC-004 with no live proxy dependency in tests.

**Checkpoint**: AI can adjust context only through the approved bounded contract; all failures produce policy-only results.

---

## Phase 5: User Story 3 - Database-Backed Identity Context (Priority: P1)

**Goal**: Rich imports and profiles share stable IDs, baselines, policy results, AI status, and assessments.

- [ ] T029 [P] [US3] Create/revise `sentinel-access/backend/tests/unit/test_identity_resolution.py` for stable ID, principal/display changes, ambiguity, legacy compatibility, duplicate IDs, and unresolved identities.
- [ ] T030 [P] [US3] Create `sentinel-access/backend/tests/contract/test_identity_profiles.py` for additive card fields, profile limits, baseline, policy/AI risk summary, assessment immutability, timeline stable-ID lookup, and 404s.
- [ ] T031 [US3] Complete `sentinel-access/backend/app/services/identity_resolution.py` and transactional identity/event store methods; stable `identityId` is authoritative and name fallback is unique-only/deprecated. (Depends on T029.)
- [ ] T032 [US3] Extend `sentinel-access/backend/app/routers/datasets.py` for identity/event JSON/JSONL modes, atomic writes, duplicate counts, unresolved-identity rejection, and the revised no-score runtime event contract.
- [ ] T033 [US3] Update `sentinel-access/backend/app/routers/identities.py` and store profile queries for recent events, latest baseline, matched policies, AI status, floors, final score, and immutable assessment history. (Depends on T030–T032.)
- [ ] T034 [P] [US3] Add typed revised policy/AI assessment/profile helpers to `sentinel-access/client/src/lib/api.ts`.
- [ ] T035 [US3] Refactor Identity Profiles in `sentinel-access/client/src/components/WorkspaceViews.tsx` to select by `identityId`, fetch stored profile context, and render policy score/matches, AI adjustment/status, floor, final score, and evidence without local fixture fallback. (Depends on T033–T034.)
- [ ] T036 [US3] Add `sentinel-access/backend/tests/integration/test_identity_ingestion.py` proving immediate profile visibility, display-name independence, transaction rollback, duplicate idempotency, unresolved safety, and SC-005/SC-007.

**Checkpoint**: The profile the analyst sees is the context policies and AI actually used.

---

## Phase 6: User Story 4 - Versioned Policy Operations (Priority: P2)

**Goal**: Operators can inspect/toggle safe rules; only future evaluations change.

- [ ] T037 [P] [US4] Update policy contract tests in `sentinel-access/backend/tests/contract/test_policies_reports_configuration.py` for stable rule IDs, condition keys, points, floors, versions, toggle-by-ID, and 404.
- [ ] T038 [US4] Update `sentinel-access/backend/app/routers/policies.py` and store methods to return the additive `contracts/policies.md` shape and toggle by `ruleId`; prohibit API edits to condition, points, floor, or version.
- [ ] T039 [US4] Update the Policies section in `sentinel-access/client/src/components/WorkspaceViews.tsx` to display points/floors/version and toggle by stable ID while retaining existing visual behavior.
- [ ] T040 [US4] Add `sentinel-access/backend/tests/integration/test_policy_history.py`: toggle a matching rule, create before/after assessments, and prove the historical policy snapshot/results never mutate.

**Checkpoint**: Policy configuration is explicit, safe, and historically auditable.

---

## Phase 7: User Story 5 - Synthetic Telemetry and Oracle (Priority: P2)

**Goal**: Generate deterministic, demo-safe runtime data and separate mocked AI/oracle coverage.

- [ ] T041 [US5] Create/revise `sentinel-access/backend/scripts/generate_risk_scoring_data.py` with fixed seed, 20–30 fictitious identities, 30 days and 5,000–10,000 chronological normal events, reserved/documentation IPs, and no credential-like values.
- [ ] T042 [US5] Inject evaluation sequences covering every Policy Catalog rule, all allowed AI adjustments, confidence/evidence/mitigation validation failures, High/Critical floors, severity boundaries, low-confidence identities, duplicates, and unresolved identities.
- [ ] T043 [US5] Generate `datasets/risk-scoring/identities.json`, `baseline-events.jsonl`, `evaluation-events.jsonl`, `mock-ai-decisions.json`, and `expected-assessments.json`; confirm runtime files contain no mock answer or expected label.
- [ ] T044 [P] [US5] Create `sentinel-access/backend/tests/integration/test_synthetic_scenarios.py` to import runtime files, mock AI from the separate decision file, and compare every rule/AI/floor/final result against the oracle.
- [ ] T045 [P] [US5] Create `sentinel-access/backend/tests/unit/test_synthetic_data_safety.py` for deterministic output, identity references, timestamps, reserved IPs, forbidden expected-label keys, and secret/token patterns.
- [ ] T046 [US5] Run T044–T045 twice from fresh state and satisfy SC-006–SC-008.

---

## Phase 8: Polish and Full Verification

- [ ] T047 Reconcile legacy `activity_log` projection so one rich event appears once in Activity Explorer and normal-history imports do not trigger AI calls.
- [ ] T048 Run `.venv\Scripts\python.exe -m pytest tests/unit tests/contract tests/integration` and fix all regressions without weakening policy/AI assertions.
- [ ] T049 Run `pnpm check` and `pnpm build` in `sentinel-access/`; verify typed revised contracts and frontend rendering.
- [ ] T050 Execute `quickstart.md` with FastAPI + Vite, inspect browser requests, and verify the full event → baseline → policy → AI/fallback → floor → assessment → profile flow.
- [ ] T051 Search runtime code/contracts/tests for `IsolationForest`, `isolationForestScore`, `securityContextScore`, and former weighted formula fields; remove remaining Feature 004 references except explicit supersession notes in documentation.
- [ ] T052 Review diffs for demo safety and existing user changes, confirm no `.env`/API key/real data entered the patch, and record SC-001–SC-008 evidence in the handoff.

---

## Dependencies

```text
Reconciliation T001–T004
    ↓
Foundation T005–T009
    ↓
Policy MVP T010–T020
    ├── AI context T021–T028
    └── Identity context T029–T036
             └── Policy operations T037–T040

Policy + AI + Identity + Policies → Synthetic T041–T046 → Verification T047–T052
```

## Implementation Strategy

1. Stop after T004 and verify the superseded formula is gone without losing stable-ID work.
2. Deliver policy-only MVP through T020; it must work with AI unavailable.
3. Add bounded AI and satisfy every zero-adjustment failure path.
4. Complete database profiles and safe policy toggles.
5. Generate the oracle-backed synthetic demo and run full verification.

## Notes

- The worktree contains partial user-approved and superseded edits; never reset or overwrite unrelated changes.
- Mark a task complete only after its tests/checkpoint pass.
- Any change to catalog points, adjustment set, confidence threshold, floor order, or formulas returns to the spec review gate.
