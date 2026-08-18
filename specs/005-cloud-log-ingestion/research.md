# Phase 0 Research: Cloud Log Ingestion and Raw Replay

## 1. MVP ingestion transport

**Decision**: Accept provider-native synthetic files through a new multipart FastAPI endpoint and process them synchronously.

**Rationale**: The application already runs as one local FastAPI process. A file upload proves the raw-first boundary without adding credentials, cloud SDKs, long-running workers, or a broker.

**Alternatives considered**:

- Live provider polling/subscriptions: deferred because credentials, network setup, checkpointing, and provider-specific delivery semantics are separate production concerns.
- A queue between archive and normalization: rejected for the hackathon scale; the batch/attempt state model preserves a future asynchronous seam.
- Reusing `POST /api/datasets`: rejected because that endpoint represents already-normalized imports and would blur raw versus normalized contracts.

## 2. Raw-store implementation

**Decision**: Store exact uploaded bytes beneath a configurable local filesystem root using generated batch paths, a temporary file, digest verification, and atomic rename. Store searchable batch/record metadata in existing process-local SQLite.

**Rationale**: A filesystem archive preserves the exact input and enables replay while staying local and dependency-free. SQLite is better for status and lineage queries than scanning directories.

**Alternatives considered**:

- Store raw payloads only in SQLite: rejected because large provider files inflate the process-local database and do not model an object-store migration cleanly.
- Store only per-record canonical JSON: rejected because parsing/reserialization loses the exact uploaded evidence.
- Add S3/MinIO: deferred because it introduces an external service that is unnecessary for the local MVP.

## 3. Batch and record identity

**Decision**: Identify a batch by a generated stable batch ID plus its SHA-256 digest. Identify each raw record from provider, source-account scope, and native event ID; if the native ID is absent, use a canonical JSON content digest within provider/source scope.

**Rationale**: Provider native IDs are the best retry keys but are not globally unique. Content hashing gives deterministic fallback behavior without trusting filenames.

**Alternatives considered**:

- Random raw-event IDs: rejected because retries could not be recognized deterministically.
- Hash only the complete batch: rejected because the same record can arrive in different batches.
- Hash raw record bytes without provider/source scope: rejected because legitimate identical records from different accounts could collide.

## 4. Raw fidelity and extraction

**Decision**: Preserve the entire uploaded file byte-for-byte and index each parsed record by zero-based record index, native ID, and content digest. Replay parses the archived batch again using the same provider parser.

**Rationale**: This preserves evidence while avoiding a second raw copy per record. Record indexes provide traceability back into the archived object.

**Alternatives considered**:

- Split every record into a separate file: rejected because it adds many writes and canonicalization ambiguity at demo scale.
- Preserve only valid records: rejected because malformed records are often the evidence needed to fix parsers.

## 5. Normalized contract boundary

**Decision**: Provider normalizers output feature 004's `NormalizedSecurityEventV1` exactly. Raw lineage remains in feature-005 metadata using `raw_event_id → event_id`, rather than embedding the entire raw payload in `security_events`.

**Rationale**: The Context Builder needs a small stable event contract. Keeping raw payloads separate avoids noisy, sensitive, and attacker-controlled fields entering queries or prompts by default.

**Alternatives considered**:

- Let the Context Builder parse raw provider payloads: rejected because it duplicates provider logic and makes baselines inconsistent.
- Add every provider field to the normalized table: rejected because the schema would become unstable and sparse.

## 6. Identity resolution

**Decision**: Resolve provider principals using a versioned binding keyed by `(provider, source_account_id, principal_key)` and return one stable feature-004 `identityId`.

**Rationale**: Provider principals vary across ARN, object ID, email, and service-account formats. Explicit bindings are auditable and prevent display-name collisions.

**Alternatives considered**:

- Use display names or email normalization heuristics: rejected because renames/collisions can attach security events to the wrong profile.
- Let feature 004 guess identities later: rejected because its contract requires `identityId` on accepted normalized events.

## 7. Provider normalization scope

**Decision**: Support representative management/audit records from AWS CloudTrail, Azure Activity Log, and GCP Audit Log. Preserve the native action string and normalize only common context fields.

**Rationale**: Native actions are useful for feature 004's deterministic/LLM classifier, while common actor/time/source/service/resource/outcome fields are enough for baselines.

**Provider mappings**:

- AWS: `eventID`, `eventTime`, `userIdentity`, `sourceIPAddress`, `eventSource`, `eventName`, `resources`, `responseElements/errorCode`, `userAgent/sessionContext`.
- Azure: `eventDataId`, `eventTimestamp`, `claims`, `caller`, `resourceProviderName`, `operationName`, `resourceId`, `status`, `correlationId`.
- GCP: `insertId`, `timestamp`, `protoPayload.authenticationInfo`, `requestMetadata.callerIp`, `serviceName`, `methodName`, `resourceName`, `status`, `operation.id`.

## 8. Quarantine semantics

**Decision**: Use a closed reason-code enum and store bounded diagnostics plus raw lineage. Initial codes are `invalid_json`, `unsupported_shape`, `missing_native_fields`, `invalid_event_time`, `unresolved_identity`, `normalization_validation_failed`, and `publication_failed`.

**Rationale**: Closed codes support reliable tests/dashboards while bounded messages provide debugging context without copying raw payloads into error tables.

## 9. Replay and publication

**Decision**: Replay targets a known batch and supported normalizer version. Each raw-record/version/mapping-version attempt is idempotent. Results validate in memory before publication; changed event IDs are returned for an explicit downstream context rebuild.

**Rationale**: Reprocessing should repair normalization without silently recalculating risk or overwriting historical evidence.

**Alternatives considered**:

- Automatically invoke feature 004 scoring: rejected because replay scope and LLM cost must be explicit.
- Overwrite existing assessment inputs: rejected because historical assessments must remain reproducible.

## 10. Synthetic data design

**Decision**: Add a stdlib-only generator with a fixed anchor time, fixed seed/version, deterministic IDs, documentation-reserved IPs, and provider-native runtime files. Put identity bindings and expected normalization in separate files.

**Rationale**: The existing behavioral dataset is not provider-native and contains runtime labels/risk scores. A separate pack tests ingestion faithfully and remains safe and reproducible.

**Generated files**:

```text
datasets/cloud-ingestion/
├── aws-cloudtrail.json
├── azure-activity-log.json
├── gcp-audit-log.jsonl
├── identity-bindings.json
├── expected-normalized-events.jsonl
└── manifest.json
```

## 11. Limits and security

**Decision**: Limit uploads to 25 MiB and 10,000 records, reject compressed files, generate all storage paths, and treat every raw field as untrusted.

**Rationale**: These controls cover the principal local-demo risks: memory exhaustion, path traversal, decompression bombs, prompt injection, and accidental secret leakage.

## Outstanding NEEDS CLARIFICATION

None. The following defaults are selected for the MVP: three provider formats, synchronous upload, local filesystem archive, no live connectors, no broker, and no automatic risk rescoring.
