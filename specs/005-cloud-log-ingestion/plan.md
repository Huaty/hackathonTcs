# Implementation Plan: Cloud Log Ingestion, Raw Event Storage, and Normalization

**Branch**: `005-cloud-log-ingestion` | **Date**: 2026-08-18 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/005-cloud-log-ingestion/spec.md`

## Summary

Extend the existing local FastAPI backend with a raw-first synthetic cloud-log ingestion boundary. Exact AWS CloudTrail, Azure Activity Log, and GCP Audit Log uploads are archived beneath a configurable application-owned directory, indexed in the existing process-local SQLite database, normalized deterministically into feature 004's stable event contract, and linked through versioned lineage. Invalid/unresolved records are quarantined, duplicate records are idempotent, and archived batches can be synchronously replayed without invoking the LLM or risk scorer. A stdlib-only deterministic synthetic generator supplies provider-native runtime fixtures, identity bindings, a separate expected-normalization oracle, and a digest manifest.

## Technical Context

**Language/Version**: Python 3.11+ backend; TypeScript 5.6 + React 19 only if a later status view is added

**Primary Dependencies**: FastAPI, Pydantic v2, Python stdlib `sqlite3`, `hashlib`, `json`, `pathlib`, `tempfile`, and `os.replace`; no provider SDKs

**Storage**: Exact raw batch files under configurable local `RAW_EVENT_STORE_PATH`; ingestion metadata in existing process-local SQLite; normalized events published through feature 004 storage methods

**Testing**: `pytest`, FastAPI `TestClient`, parser/normalizer unit tests, filesystem atomicity tests using temporary directories, contract tests, replay/idempotency integration tests, generated-fixture oracle tests

**Target Platform**: Local single-process FastAPI service on port 8001; Windows-compatible paths and atomic same-filesystem rename

**Project Type**: Existing React + FastAPI web application; backend-first feature

**Performance Goals**: Archive and synchronously normalize the generated fixture pack in under 10 seconds; deterministic normalization under 5 ms per record at demo scale; batch/status retrieval under 200 ms

**Constraints**: Synthetic uploads only; 25 MiB and 10,000-record caps; exact-byte archive precedes publication; stable IDs; generated paths; no compressed input; no live cloud access; no broker/worker/managed store; no LLM or scoring calls

**Scale/Scope**: Three provider formats, one local operator, tens to thousands of synthetic records per batch, one FastAPI process

## Constitution Check

*GATE: Passed with one explicitly scoped storage extension. Re-check after Phase 1 design.*

| Principle | Check | Result |
|---|---|---|
| I. API-First Backend Migration | Upload, batch status, replay creation, and replay status contracts are defined before implementation. | PASS |
| II. Preserve Existing UX and Data Shapes | New endpoints are additive. Existing `/api/datasets`, Activity, Identity, Command Center, and dashboard contracts remain unchanged. | PASS |
| III. Scoped Demo Infrastructure and YAGNI | The feature adds only a local filesystem raw archive plus SQLite metadata. It explicitly rejects brokers, cloud SDKs, managed object stores, and production connectors. | PASS WITH JUSTIFICATION |
| IV. Contract Clarity Before Implementation | Provider inputs, normalized output, identity binding, error semantics, and REST contracts are documented before tasks. | PASS |
| V. Demo-Safe Data Only | All runtime inputs are generated synthetic provider records using documentation IPs; labels/oracles are separate. Real customer telemetry remains out of scope. | PASS |

**Post-Design Re-check**: The raw archive is the smallest infrastructure that can preserve exact bytes and support replay. Paths are application-generated, payloads remain outside prompts, SQLite remains the searchable metadata/index store, and no external service is introduced. All gates pass for the approved synthetic MVP.

## Project Structure

### Documentation (this feature)

```text
specs/005-cloud-log-ingestion/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── ingestion.md
│   ├── normalized-event.md
│   └── replay.md
├── checklists/
│   └── requirements.md
└── tasks.md
```

### Source Code (repository root)

```text
datasets/cloud-ingestion/
├── generate_raw_cloud_logs.py
├── aws-cloudtrail.json
├── azure-activity-log.json
├── gcp-audit-log.jsonl
├── identity-bindings.json
├── expected-normalized-events.jsonl
└── manifest.json

sentinel-access/backend/
├── .gitignore                         # ignore configured runtime raw archive
├── app/
│   ├── config.py                      # raw-store path and limits
│   ├── db.py                          # ingestion/replay lineage tables
│   ├── store.py                       # typed ingestion metadata CRUD/transactions
│   ├── schemas/entities.py            # request/response and domain schemas
│   ├── services/
│   │   ├── raw_event_store.py         # exact-byte atomic archive adapter
│   │   ├── ingestion.py               # batch orchestration and provider dispatch
│   │   ├── identity_bindings.py       # stable provider principal resolution
│   │   └── normalizers/
│   │       ├── __init__.py
│   │       ├── common.py
│   │       ├── aws_cloudtrail.py
│   │       ├── azure_activity_log.py
│   │       └── gcp_audit_log.py
│   └── routers/
│       └── ingestion.py               # upload/status/replay endpoints
└── tests/
    ├── unit/
    │   ├── test_raw_event_store.py
    │   └── test_cloud_normalizers.py
    ├── contract/
    │   └── test_ingestion_api.py
    └── integration/
        ├── test_cloud_ingestion_pipeline.py
        └── test_ingestion_replay.py
```

**Structure Decision**: Extend the existing FastAPI backend rather than create an ingestion microservice. Keep provider-specific parsing in isolated normalizer modules and filesystem persistence behind one adapter so a future object store can replace it without changing the normalized contract.

## Delivery Phases

### Phase 0 - Freeze boundaries

1. Confirm synthetic uploaded files, not live cloud connectors, are the MVP transport.
2. Freeze provider/source identity, raw-event ID, normalized-event, and quarantine semantics.
3. Confirm replay returns affected event IDs but does not run feature 004 context/scoring.

### Phase 1 - Synthetic fixtures and contracts

1. Generate deterministic provider-native inputs, identity bindings, expected oracle, and manifest.
2. Validate that runtime inputs contain no labels, scores, real identities, routable IPs, or secrets.
3. Define upload/status/replay contracts and provider mapping rules.

### Phase 2 - Raw-first foundation

1. Add configuration, schema, transaction primitives, and typed metadata models.
2. Implement exact-byte temporary-write, digest verification, and atomic archive rename.
3. Parse provider envelopes and index stable raw-event records/occurrences.

### Phase 3 - Deterministic normalization

1. Implement explicit source-identity bindings.
2. Implement AWS, Azure, and GCP normalizers against one shared output schema.
3. Publish valid events through the feature-004 storage boundary and quarantine failures.
4. Verify output against the generated oracle.

### Phase 4 - Replay and integration

1. Implement replay from known batch IDs and target versions.
2. Record attempts, unchanged/changed outputs, quarantine outcomes, and affected event IDs.
3. Verify repeated uploads/replays are idempotent and never invoke scoring/LLM code.

### Phase 5 - Full verification

1. Run generator determinism and safety checks.
2. Run backend unit/contract/integration suites and frontend regression checks.
3. Execute quickstart end to end against a fresh backend/raw-store root.

## Complexity Tracking

| Variation | Why Needed | Simpler Alternative Rejected Because |
|---|---|---|
| Add a local filesystem raw archive alongside process-local SQLite | Reprocessing requires the exact original bytes to outlive parsing and normalization attempts. This specification is the constitution-required gate for that bounded durable storage. | SQLite-only raw blobs conflate searchable relational state with large immutable objects and make an object-store migration harder. Keeping only canonical records would lose the exact upload. |
| Three provider normalizers | The user requested cloud-log ingestion and the dashboard currently represents multiple clouds. Three small explicit parsers demonstrate the provider-independent boundary credibly. | A single generic flat CSV would repeat the existing dataset importer and would not test provider-native normalization. |

## Cross-feature dependency

Feature 005 depends on feature 004's normalized event model and stable identity IDs for final publication. Work can proceed independently through parser/normalizer oracle tests. Final integration tasks must not invent a second normalized schema or bypass feature 004's idempotent `security_events` storage methods.
