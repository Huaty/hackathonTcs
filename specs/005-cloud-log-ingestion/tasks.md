---
description: "Implementation tasks for raw cloud-log ingestion, normalization, replay, and deterministic synthetic fixtures"
---

# Tasks: Cloud Log Ingestion, Raw Event Storage, and Normalization

**Input**: Design documents from `/specs/005-cloud-log-ingestion/`

**Prerequisites**: `spec.md`, `plan.md`, `research.md`, `data-model.md`, `contracts/`, feature 004 normalized-event schemas for final publication

**Tests**: Required by SC-001 through SC-008. Archive fidelity, normalizer oracle, idempotency, quarantine, replay, and synthetic safety tests are implementation gates.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can proceed in parallel after listed dependencies because it touches a separate file/concern.
- **[Story]**: Maps to `spec.md` User Story 1–4.
- Paths are relative to repository root.

## Phase 1: Setup and fixture contract

- [ ] T001 Add `RAW_EVENT_STORE_PATH`, `MAX_RAW_UPLOAD_BYTES=26214400`, and `MAX_RAW_RECORDS=10000` settings in `sentinel-access/backend/app/config.py`, defaulting the runtime archive beneath an ignored backend `.runtime/` directory.
- [ ] T002 Update `sentinel-access/backend/.gitignore` to exclude the runtime raw-store directory without ignoring `datasets/cloud-ingestion/` fixtures.
- [ ] T003 [P] Add shared provider, batch-status, attempt-status, quarantine-reason, normalizer-version, and mapping-version enums/models to `sentinel-access/backend/app/schemas/entities.py`.
- [ ] T004 [P] Add generator determinism/safety tests in `sentinel-access/backend/tests/unit/test_cloud_ingestion_fixtures.py` covering manifest digests, reserved IPs, forbidden label/secret keys, identity binding references, native IDs, and byte-identical regeneration.
- [ ] T005 Run `datasets/cloud-ingestion/generate_raw_cloud_logs.py --check` and T004; fix the generator/fixtures without introducing runtime expected labels.

**Checkpoint**: Configuration and deterministic provider fixture contracts are stable; runtime behavior is unchanged.

---

## Phase 2: Foundational lineage and storage (Blocking)

- [ ] T006 Extend `sentinel-access/backend/app/db.py` with `ingestion_batches`, `raw_event_records`, `raw_event_occurrences`, `source_identity_bindings`, `normalization_attempts`, `quarantine_records`, and `replay_runs` tables/indexes from `data-model.md` while preserving feature-004 and legacy tables.
- [ ] T007 Extend the feature-004 transaction helper in `sentinel-access/backend/app/db.py` so metadata/publication operations can commit atomically without holding the lock during filesystem I/O.
- [ ] T008 Extend `sentinel-access/backend/app/store.py` with typed batch, raw-record occurrence, binding, attempt, quarantine, and replay CRUD methods; do not return raw SQLite rows from public methods.
- [ ] T009 [P] Create `sentinel-access/backend/tests/unit/test_raw_event_ids.py` covering provider/source scoping, native-ID collisions, canonical hash fallback, deterministic event IDs, and canonical JSON hashing.
- [ ] T010 Implement common stable-ID, canonical JSON, timestamp, IP, outcome, and bounded-diagnostic helpers in `sentinel-access/backend/app/services/normalizers/common.py` until T009 passes.
- [ ] T011 Run existing backend storage/contract tests and resolve schema regressions before starting user stories.

**Checkpoint**: Typed lineage storage and deterministic identifier primitives are ready.

---

## Phase 3: User Story 1 - Raw-first batch ingestion (Priority: P1) 🎯 MVP slice

**Goal**: Archive exact uploaded bytes, parse/index provider records, and report duplicates/quarantine without losing a batch.

### Tests

- [ ] T012 [P] [US1] Create `sentinel-access/backend/tests/unit/test_raw_event_store.py` covering temporary writes, exact digest/size, generated paths, atomic rename, cleanup after failure, path-containment checks, and read-time digest verification.
- [ ] T013 [P] [US1] Create ingestion contract tests in `sentinel-access/backend/tests/contract/test_ingestion_api.py` for all three providers, required query fields, limits, unsupported/compressed inputs, response counts, bounded errors, status pagination, and archive-failure semantics.

### Implementation

- [ ] T014 [US1] Implement the local filesystem adapter in `sentinel-access/backend/app/services/raw_event_store.py` against T012; all resolved paths must remain beneath the configured root.
- [ ] T015 [US1] Implement provider envelope readers and record extraction dispatch in `sentinel-access/backend/app/services/ingestion.py` for AWS `Records`, Azure `records`, and GCP JSONL with the approved limits.
- [ ] T016 [US1] Add archive-first batch orchestration, batch/record indexing, duplicate-batch/raw-record detection, occurrence tracking, and aggregate status/count updates in `sentinel-access/backend/app/services/ingestion.py`.
- [ ] T017 [US1] Create `sentinel-access/backend/app/routers/ingestion.py` with `POST /api/ingestion/batches` and `GET /api/ingestion/batches/{batchId}` exactly as `contracts/ingestion.md`.
- [ ] T018 [US1] Register the ingestion router in `sentinel-access/backend/app/main.py` without changing `/api/datasets` behavior.
- [ ] T019 [US1] Run T012–T013 and existing dataset/activity tests; prove exact-byte preservation occurs before any normalized publication.

**Checkpoint**: Raw provider batches are safely archived/indexed and inspectable even before feature-004 publication is connected.

---

## Phase 4: User Story 2 - Provider normalization (Priority: P1)

**Goal**: Deterministically convert supported raw records into feature 004's stable normalized event contract and quarantine invalid/unresolved records.

### Tests

- [ ] T020 [P] [US2] Create `sentinel-access/backend/tests/unit/test_cloud_normalizers.py` comparing AWS, Azure, and GCP outputs with `datasets/cloud-ingestion/expected-normalized-events.jsonl`, including missing optional values and all quarantine reasons.
- [ ] T021 [P] [US2] Create `sentinel-access/backend/tests/unit/test_identity_bindings.py` covering provider/account/principal scoping, mapping versions, duplicate bindings, unresolved principals, and missing feature-004 identities.
- [ ] T022 [P] [US2] Create `sentinel-access/backend/tests/integration/test_cloud_ingestion_pipeline.py` to ingest all three runtime fixtures, verify oracle results/counts/lineage, and prove re-upload idempotency.

### Implementation

- [ ] T023 [US2] Implement binding fixture loading and exact versioned lookup in `sentinel-access/backend/app/services/identity_bindings.py` until T021 passes.
- [ ] T024 [P] [US2] Implement AWS CloudTrail parsing/mapping in `sentinel-access/backend/app/services/normalizers/aws_cloudtrail.py`.
- [ ] T025 [P] [US2] Implement Azure Activity Log parsing/mapping in `sentinel-access/backend/app/services/normalizers/azure_activity_log.py`.
- [ ] T026 [P] [US2] Implement GCP Audit Log parsing/mapping in `sentinel-access/backend/app/services/normalizers/gcp_audit_log.py`.
- [ ] T027 [US2] Add normalized-model validation, attempt persistence, closed-code quarantine, and `rawEventId → eventId` lineage orchestration to `sentinel-access/backend/app/services/ingestion.py`.
- [ ] T028 [US2] Connect normalized publication to feature 004's idempotent security-event store method; reject conflicting same-`eventId` content rather than overwriting it.
- [ ] T029 [US2] Complete T020/T022 and verify SC-002–SC-004 without calling liteLLM, the Context Builder, or risk-scoring services.

**Checkpoint**: Every supported valid provider record produces one verified feature-004 event; every controlled failure is quarantined safely.

---

## Phase 5: User Story 3 - Replay archived batches (Priority: P2)

**Goal**: Re-run known archived bytes under a supported version and expose unchanged/changed/quarantined outcomes without automatic rescoring.

### Tests

- [ ] T030 [P] [US3] Create `sentinel-access/backend/tests/integration/test_ingestion_replay.py` covering digest verification, same-version idempotency, new-version attempt lineage, failed validation, affected event IDs, missing/corrupt archives, and proof no AI/risk endpoints are invoked.
- [ ] T031 [P] [US3] Extend `test_ingestion_api.py` for replay request/response validation and 200/201/400/404/409/422 behavior.

### Implementation

- [ ] T032 [US3] Implement replay orchestration in `sentinel-access/backend/app/services/ingestion.py`, selecting only indexed batch IDs, verifying archived digests, and recording per-record versioned attempts.
- [ ] T033 [US3] Add `POST /api/ingestion/replays` and `GET /api/ingestion/replays/{replayId}` to `sentinel-access/backend/app/routers/ingestion.py` exactly as `contracts/replay.md`.
- [ ] T034 [US3] Return changed `affectedEventIds` for an explicit future feature-004 context rebuild while leaving existing assessments untouched.
- [ ] T035 [US3] Run T030–T031 twice from fresh state and confirm deterministic counts and zero duplicate event IDs.

**Checkpoint**: The raw archive provides safe, auditable reprocessing value.

---

## Phase 6: User Story 4 - Synthetic provider pack (Priority: P2)

**Goal**: Keep the checked-in provider-native data reproducible, realistic enough for demonstrations, and completely demo-safe.

- [ ] T036 [US4] Review `datasets/cloud-ingestion/generate_raw_cloud_logs.py` against provider fixtures and add any missing controlled cases without changing the approved contract.
- [ ] T037 [US4] Regenerate all six output files and review diffs for deterministic IDs/times, fictitious values, reserved IPs, runtime/oracle separation, counts, and digests.
- [ ] T038 [US4] Run generator `--check`, T004, T020, and T022 twice; record SC-006/SC-007 evidence.

**Checkpoint**: Anyone can reproduce and verify the complete demo pack offline.

---

## Phase 7: Polish and full-story verification

- [ ] T039 Reconcile feature-004 implementation dependencies and ensure one rich event appears once in Activity/Identity views after raw ingestion.
- [ ] T040 [P] Add structured application logs for batch/replay IDs and aggregate counts without logging raw payloads or principals.
- [ ] T041 [P] Update `specs/005-cloud-log-ingestion/quickstart.md` only if implemented commands differ; contract changes return to spec review.
- [ ] T042 Run all backend tests, `npm run check`, and `npm run build`; resolve regressions without weakening archive, identity, or idempotency assertions.
- [ ] T043 Execute quickstart against a fresh raw root; verify archive hashes, oracle output, duplicate uploads, replay, and downstream event visibility.
- [ ] T044 Review diffs for `.env`, runtime raw archives, real-looking data, tokens/secrets, expected-label leakage, and accidental changes to existing user work.

## Dependencies and execution order

```text
T001–T011 foundation
    └── T012–T019 raw ingestion (US1)
            ├── T020–T029 normalization (US2)
            │       └── T030–T035 replay (US3)
            └── T036–T038 fixture hardening (US4)

All desired stories → T039–T044 verification
```

- Final T028 publication depends on feature 004's stable normalized-event/store implementation.
- Raw-store and provider-normalizer unit work can proceed before T028.
- Provider normalizers T024–T026 are parallel after shared common helpers/bindings stabilize.

## Implementation strategy

1. Complete the deterministic fixture and lineage foundation.
2. Ship raw archive + batch status as the first independently testable slice.
3. Add all provider normalizers and feature-004 publication.
4. Add replay after same-version ingestion is proven idempotent.
5. Keep live cloud connectors and asynchronous infrastructure in a later feature.

## Notes

- Preserve all unrelated dirty worktree changes.
- Do not create/switch/reset branches destructively.
- A task is complete only after its listed tests/checkpoint pass.
- Do not put runtime raw payloads, expected labels, or provider strings into LLM prompts.
