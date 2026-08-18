# Implementation Plan: Policy-First AI Contextual Risk Scoring

**Branch**: `004-contextual-risk-scoring` | **Date**: 2026-08-18 | **Spec**: [spec.md](spec.md)

**Input**: Revised feature specification from `/specs/004-contextual-risk-scoring/spec.md`

## Summary

Extend Sentinel Access so versioned deterministic policies produce an auditable base risk score and strongest severity floor, while the existing liteLLM proxy supplies only a validated contextual adjustment from the fixed set `{-15,-5,0,10,20,25}`. The server applies confidence/evidence safeguards, arithmetic, floors, and severity. AI failure becomes a zero adjustment, never a failed policy assessment. Imported telemetry remains connected to stable database-backed identities and baselines, and a five-part synthetic pack verifies every rule, adjustment, failure, and boundary.

This revision removes Isolation Forest from Feature 004. Partial implementation created under the superseded design must be reconciled before new runtime work proceeds.

## Technical Context

**Language/Version**: Python 3.11+ backend; TypeScript 5.6 + React 19 frontend

**Primary Dependencies**: FastAPI, Pydantic v2, stdlib `sqlite3`, existing `httpx`/liteLLM-compatible proxy client, Axios

**Storage**: Existing process-wide in-memory SQLite; evolve `policies` and add normalized events, baseline snapshots, AI context decisions, immutable rule results, and risk assessments

**Testing**: `pytest`, FastAPI `TestClient`, pure policy-engine unit tests, mocked AI schema/failure tests, API contract tests, ingestion/profile integration tests, synthetic oracle verification

**Target Platform**: Local FastAPI service on port 8001 plus Vite frontend; same single-process hackathon architecture

**Project Type**: Existing React web application with FastAPI backend

**Performance Goals**: Policy evaluation under 50 ms per event; identity profile under 200 ms at demo scale; AI timeout remains 15 seconds; normal-history imports do not trigger one AI call per event

**Constraints**: No AI-generated rule/point/floor/arithmetic; adjustments only from approved set; AI confidence threshold 0.60; valid evidence IDs required; floors applied after AI; stable identity/event IDs; prompt fields untrusted; no Isolation Forest inputs or dependencies

**Scale/Scope**: 20–30 identities, 30 days and 5,000–10,000 synthetic historical events, tens of evaluated events, bounded 20-event/60-minute sequences, one analyst/backend process

## Constitution Check

*GATE: Re-checked after scoring-model revision on 2026-08-18.*

| Principle | Check | Result |
|---|---|---|
| I. API-First Backend Migration | Contracts define policies, assessment, identities, and import behavior before revised implementation resumes. | PASS |
| II. Preserve Existing UX and Data Shapes | Existing card/activity/policy fields remain; rule and AI details are additive. | PASS |
| III. Scoped Demo Infrastructure and YAGNI | Uses approved process-local SQLite and bounded liteLLM proxy only; no new managed infrastructure. | PASS |
| IV. Contract Clarity Before Implementation | Formula, policy catalog, prompt schema, failure rules, and REST contracts are explicit. | PASS |
| V. Demo-Safe Data Only | Runtime prompts contain synthetic data; mock AI answers/oracles remain test-only. | PASS |

**Post-Design Re-check**: The revised data model removes the Isolation Forest field, records immutable policy snapshots/results and bounded AI decisions, and retains stable identity/baseline work. All gates PASS.

## Project Structure

### Documentation

```text
specs/004-contextual-risk-scoring/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── datasets.md
│   ├── identities.md
│   ├── policies.md
│   └── risk-assessments.md
├── checklists/requirements.md
└── tasks.md
```

### Source code

```text
datasets/risk-scoring/
├── identities.json
├── baseline-events.jsonl
├── evaluation-events.jsonl
├── mock-ai-decisions.json
└── expected-assessments.json

sentinel-access/
├── backend/
│   ├── app/
│   │   ├── db.py
│   │   ├── seed_data.py
│   │   ├── store.py
│   │   ├── ai_client.py
│   │   ├── schemas/entities.py
│   │   ├── services/
│   │   │   ├── baseline.py
│   │   │   ├── policy_engine.py
│   │   │   ├── ai_risk_context.py
│   │   │   ├── identity_resolution.py
│   │   │   └── risk_scoring.py
│   │   └── routers/
│   │       ├── datasets.py
│   │       ├── identities.py
│   │       ├── policies.py
│   │       └── risk_assessments.py
│   ├── scripts/generate_risk_scoring_data.py
│   └── tests/{unit,contract,integration}/
└── client/src/
    ├── components/WorkspaceViews.tsx
    └── lib/api.ts
```

**Structure Decision**: Keep routers transport-only and put baseline, policy, AI validation, and final arithmetic into independently testable services. Store approved condition keys in SQLite, but implement condition behavior in `policy_engine.py` rather than executing database expressions. Keep the synthetic oracle outside runtime inputs.

## Delivery Phases

### Phase 0 - Reconcile superseded partial implementation

1. Preserve stable identity/event/baseline schema work that conforms to the revision.
2. Remove Isolation Forest request/storage/response fields and weighted-context arithmetic.
3. Replace action-classification AI authority with policy conditions plus the bounded AI context schema.
4. Rewrite partially created tests to assert the revised contract.

### Phase 1 - Policy foundation

1. Seed/evolve Policy Catalog v1 with approved condition keys, points, floors, enabled state, and version.
2. Implement baseline/context inputs and deterministic rule evaluation.
3. Persist complete immutable rule results and policy snapshot version.
4. Verify aggregation, double-count prevention, caps, disabled rules, unknown baselines, and floors.

### Phase 2 - AI context and final scoring

1. Build a fixed versioned prompt with bounded event sequence and untrusted-data delimiters.
2. Validate adjustment, confidence, evidence IDs, mitigation, and explanation.
3. Apply zero on every invalid/unavailable/low-confidence path.
4. Calculate clamp, floor, final score, severity, provenance, cache key, and idempotency.

### Phase 3 - Identity ingestion and profiles

1. Complete transactional identity/event import and stable-ID resolution.
2. Expose profiles containing baseline, rule results, AI status, and assessments.
3. Update Identity Profiles without local fixture fallback.

### Phase 4 - Policy operations

1. Extend the existing policy API/UI with rule identity, points, floor, version, and enabled state.
2. Ensure toggles affect future snapshots only.
3. Prove historical assessments remain immutable.

### Phase 5 - Synthetic validation

1. Generate normal history and controlled evaluation sequences.
2. Keep mock AI decisions/oracle separate from runtime events.
3. Verify every catalog rule, adjustment, failure path, floor, boundary, and join.
4. Run full backend/frontend/browser regression verification.

## Complexity Tracking

| Complexity | Why Needed | Simpler Alternative Rejected Because |
|---|---|---|
| Immutable policy snapshots/results | Historical auditability requires an assessment to retain the exact enabled rules, points, floors, and version used. | Reading current policy rows would rewrite the meaning of historical scores after a toggle. |
| External liteLLM context call | The project owner explicitly wants prompt-driven AI context in the score. Its influence is tightly bounded and optional. | Policy-only scoring remains the fallback but cannot describe cross-event intent, blast radius, and mitigation as flexibly. |
| Separate AI decision entity | Raw versus applied adjustment, validation status, evidence, model, and prompt version must be auditable and cacheable. | Storing only final prose/score would hide why an adjustment was accepted or rejected. |

**Revision sign-off**: Project owner changed the scoring direction on 2026-08-18 to policy base score plus bounded AI adjustment and requested the Spec Kit update. Isolation Forest is no longer part of Feature 004.
