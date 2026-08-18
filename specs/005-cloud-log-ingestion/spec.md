# Feature Specification: Cloud Log Ingestion, Raw Event Storage, and Normalization

**Feature Branch**: `005-cloud-log-ingestion`

**Created**: 2026-08-18

**Status**: Draft

**Input**: User description: "Ingest raw cloud logs, preserve an immutable raw event store, normalize provider-specific records for the contextual-risk pipeline, support replay, and provide synthetic cloud data for the MVP."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Ingest and preserve provider-native logs (Priority: P1)

A demo operator uploads a synthetic AWS CloudTrail, Azure Activity Log, or GCP Audit Log file and receives a batch result proving that the original bytes were preserved before any normalization was attempted.

**Why this priority**: The raw archive is the safety boundary for retries, audit, and future normalizer fixes. If the original payload is lost, later stages cannot reproduce what arrived.

**Independent Test**: Upload one valid fixture for each supported provider, compare the stored SHA-256 digest with the uploaded file, and confirm every extracted record has a stable raw-event identifier and batch/index lineage.

**Acceptance Scenarios**:

1. **Given** a supported provider-native file, **When** it is ingested, **Then** the exact uploaded bytes, provider, source account, receive time, digest, record count, and immutable batch ID are stored before normalization begins.
2. **Given** the same provider record is uploaded again, **When** ingestion completes, **Then** it is reported as a duplicate raw event and is not normalized into a second security event.
3. **Given** a syntactically valid batch containing one invalid record, **When** it is ingested, **Then** the batch remains preserved, valid records continue, and the invalid record is quarantined with a bounded machine-readable reason.
4. **Given** an unsupported, oversized, compressed, or structurally unreadable upload, **When** it is submitted, **Then** no normalized event is written and the response clearly explains whether an archived failed batch exists.

---

### User Story 2 - Normalize cloud records into the contextual-risk contract (Priority: P1)

The Context Builder receives one stable normalized event shape regardless of whether the source was AWS, Azure, or GCP. Provider-specific fields remain accessible through raw lineage without entering the scoring prompt by default.

**Why this priority**: Feature 004 cannot build identity baselines or score events until provider records become consistent, identity-linked normalized events.

**Independent Test**: Ingest the three synthetic provider fixtures and compare every successful output with the separate expected-normalized oracle, field for field.

**Acceptance Scenarios**:

1. **Given** equivalent read, permission-change, credential/key, and protection-change activity from different providers, **When** normalization runs, **Then** each result uses the versioned feature-004 normalized event contract while preserving the provider action name.
2. **Given** a configured provider-principal mapping, **When** a record is normalized, **Then** its stable `identityId` is resolved without display-name guessing.
3. **Given** an unknown principal, **When** normalization runs, **Then** the record is quarantined as unresolved and is never attached to an arbitrary identity.
4. **Given** a provider record with missing optional source or resource fields, **When** normalization runs, **Then** valid fields are retained, absent fields are represented as null/unknown, and no values are invented.
5. **Given** two normalization attempts for the same raw event and normalizer version, **When** both complete, **Then** they produce the same normalized event ID and do not create duplicate normalized rows.

---

### User Story 3 - Replay archived events after a normalizer change (Priority: P2)

A developer can select an archived batch and run a target normalizer version again, inspect what changed, and publish only validated normalized results. Replay does not automatically invoke contextual scoring or the LLM.

**Why this priority**: Replay is the main operational reason to retain raw logs, but the initial ingest-and-normalize path can be demonstrated without a management UI.

**Independent Test**: Replay one stored batch twice with the same normalizer version, verify identical counts/output, and confirm a later version produces separately auditable attempts without duplicating raw data.

**Acceptance Scenarios**:

1. **Given** a completed archived batch, **When** a replay is requested with a supported target version, **Then** the original bytes are re-read, normalization attempts are recorded, and raw data is not rewritten.
2. **Given** the same replay request is repeated, **When** it completes, **Then** normalized-event and attempt uniqueness rules prevent duplicates while returning the prior equivalent outcome where possible.
3. **Given** replay output fails validation, **When** the replay finishes, **Then** the current normalized event remains unchanged and the failed attempt is quarantined.
4. **Given** a successful replay changes a normalized event, **When** it is published, **Then** downstream context/scoring is marked stale or explicitly queued for a separate rebuild; the replay endpoint never calls the LLM directly.

---

### User Story 4 - Demonstrate ingestion safely with deterministic synthetic logs (Priority: P2)

A developer can regenerate provider-native demo logs and their expected normalization oracle identically on any machine without real identities, routable source addresses, credentials, tokens, or test labels leaking into runtime inputs.

**Why this priority**: The ingestion and replay paths need realistic raw shapes, duplicates, invalid records, and provider differences without using customer telemetry.

**Independent Test**: Run the generator twice, compare all file hashes, validate the manifest, and confirm runtime raw files contain no oracle-only fields or secret-like values.

**Acceptance Scenarios**:

1. **Given** the fixed generator version and seed, **When** it is run twice, **Then** every generated file is byte-for-byte identical.
2. **Given** the runtime fixtures, **When** inspected, **Then** they include all three providers, supported action families, duplicates, missing optional fields, one unresolved principal, and one malformed record without expected-result labels.
3. **Given** the expected-normalized oracle, **When** compared with runtime files, **Then** expected status, reason, normalized fields, and scenario descriptions exist only in the oracle/manifest.

### Edge Cases

- Upload size is capped at 25 MiB and candidate records at 10,000; compressed archives are rejected in the MVP.
- A batch digest match is reported as a duplicate batch; re-uploading a different file containing an existing provider event is reported as a duplicate raw record.
- Native IDs are provider-scoped: AWS `eventID`, Azure `eventDataId`, and GCP `insertId` may collide across accounts/projects without colliding globally.
- If a native event ID is absent, a canonical content hash plus provider/source scope becomes the stable raw-event key; semantically equivalent but byte-different records are not silently merged.
- Raw event time may be missing or malformed; receive time remains available, but normalization quarantines records that cannot supply a valid UTC event time.
- Events may arrive out of chronological order. Storage uses receive order for ingestion lineage and event time for normalized queries.
- One batch may contain both successful, duplicate, and quarantined records. Raw preservation is batch-atomic; normalized publication is idempotent per record.
- Provider fields are untrusted strings. They cannot select file paths, redefine mappings, choose a normalizer version, or inject instructions into the Context Builder/LLM.
- A replay cannot target raw paths supplied by the client; it selects known batch IDs from the raw-event index.
- Interrupted writes use a temporary file in the configured raw-store root followed by an atomic rename; incomplete temporary files are never indexed as complete batches.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST expose a versioned REST contract for uploading synthetic AWS CloudTrail, Azure Activity Log, and GCP Audit Log batches.
- **FR-002**: The system MUST persist the exact uploaded bytes and their SHA-256 digest successfully before attempting to publish normalized events.
- **FR-003**: Each batch MUST have an immutable `batchId`, provider, source-account identifier, received time, original filename, byte count, record count, digest, and processing status.
- **FR-004**: Each extracted record MUST have a stable provider/source-scoped `rawEventId`, batch/index lineage, native event ID when present, content digest, event time when parseable, and current processing status.
- **FR-005**: Raw batch files MUST be written only beneath a configured application-owned raw-store root using generated paths; client filenames and event fields MUST NOT control filesystem locations.
- **FR-006**: Raw batch preservation MUST be atomic. A failed archive write MUST produce no batch index marked complete and no normalized writes.
- **FR-007**: Batch ingestion MUST report total, normalized, duplicate, quarantined, and unresolved-identity counts plus at most 20 bounded row errors.
- **FR-008**: Duplicate batches and raw records MUST be detected idempotently without creating duplicate normalized security events.
- **FR-009**: Normalizers MUST convert supported provider records into the feature-004 `NormalizedSecurityEventV1` fields: stable event and identity IDs, UTC event time, source IP/location when known, service, provider action, resource, outcome, and session/correlation ID when known.
- **FR-010**: Normalization MUST be deterministic and versioned. The same raw payload, identity mapping version, and normalizer version MUST produce the same normalized result.
- **FR-011**: Provider principals MUST resolve through explicit, versioned source-identity bindings to feature-004 `identityId` values; display-name guessing is forbidden.
- **FR-012**: Unknown principals, invalid timestamps, missing required provider fields, and unsupported record shapes MUST be quarantined with a closed reason code and no normalized row.
- **FR-013**: Optional values absent from source data MUST remain null/unknown; the normalizer MUST NOT fabricate IPs, locations, resources, outcomes, or identities.
- **FR-014**: The raw-event index MUST link a successful raw record to its normalized `eventId` without requiring raw payload duplication inside the normalized event table.
- **FR-015**: The system MUST support replay by known batch ID and target normalizer version, re-reading the archived bytes and recording a versioned replay run and per-record attempt.
- **FR-016**: Replay MUST NOT modify the archived bytes, invoke the LLM, or silently overwrite the evidence/version used by an existing risk assessment.
- **FR-017**: Publishing a changed normalized result MUST return the affected `eventId` values so feature 004 can rebuild context and risk assessments explicitly.
- **FR-018**: The MVP MUST process uploads synchronously in the existing FastAPI process and MUST NOT introduce a message broker, background worker service, cloud SDK, or managed object store.
- **FR-019**: The configured MVP limits MUST be 25 MiB per upload and 10,000 candidate records; compressed inputs and unrecognized providers are rejected.
- **FR-020**: The system MUST provide deterministic synthetic runtime fixtures for all supported providers, a separate identity-mapping fixture, a separate expected-normalized oracle, and a manifest containing generator version, seed, counts, and file digests.
- **FR-021**: Runtime raw fixtures MUST contain only fictitious principals/resources, documentation-reserved IP addresses, and non-secret placeholders; expected labels and normalized answers MUST not appear in runtime raw inputs.
- **FR-022**: All stored raw/provider strings MUST be treated as untrusted data and excluded from LLM prompts by default; any later evidence selection remains bounded and allow-listed by feature 004.
- **FR-023**: The API MUST expose batch status, replay creation, and replay status contracts before implementation begins.

### Key Entities

- **Ingestion Batch**: One exact uploaded provider-native file plus immutable digest/lineage and aggregate processing state.
- **Raw Event Record**: An indexed provider record within a batch, identified independently from its normalized result.
- **Source Identity Binding**: A versioned mapping from provider/account/principal coordinates to a stable feature-004 `identityId`.
- **Normalization Attempt**: One raw record processed with one normalizer and identity-mapping version, including result or quarantine reason.
- **Quarantine Record**: A failed normalization attempt with bounded diagnostic metadata and raw lineage, never an alternative event store.
- **Replay Run**: A request to re-run a known archived batch through a target normalizer version.
- **Normalized Security Event**: The provider-independent event contract consumed by feature 004.
- **Synthetic Manifest/Oracle**: Test-only metadata and expected outcomes kept separate from runtime raw files.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For 100% of successfully accepted fixture batches, recomputing SHA-256 from the archived bytes matches the batch index digest.
- **SC-002**: For 100% of successful synthetic records, actual normalized output matches the separate expected oracle field for field.
- **SC-003**: Re-uploading every synthetic batch and replaying it twice creates zero duplicate raw-event identities and zero duplicate normalized event IDs.
- **SC-004**: Every intentionally invalid or unresolved synthetic record is quarantined under its declared closed reason code, and no valid record is quarantined.
- **SC-005**: A fresh local run ingests and synchronously processes the complete synthetic pack within 10 seconds on the hackathon development machine, excluding later contextual scoring.
- **SC-006**: Regenerating the synthetic pack twice produces identical SHA-256 digests for all generated files.
- **SC-007**: No runtime fixture contains expected-normalized fields, anomaly/risk labels, usable credentials/tokens, real personal data, or source IPs outside documentation-reserved ranges.
- **SC-008**: An operator can trace any normalized fixture event to one raw batch, record index, content digest, normalizer version, identity-mapping version, and processing attempt through API responses.

## Assumptions

- The hackathon MVP accepts uploaded synthetic files; live polling/subscription connectors and real credentials are deferred.
- AWS CloudTrail, Azure Activity Log, and GCP Audit Log are the only supported provider formats in v1.
- Feature 004 owns normalized-event storage, baseline/context construction, risk calculation, and LLM classification. Feature 005 stops after normalized publication and lineage.
- Feature 004's stable normalized-event contract is available before final integration; normalizers can be unit-tested against the contract/oracle independently.
- The local raw-store root is application-owned, excluded from Git, and configurable for tests. Moving to S3/Blob/GCS later is an adapter change, not an MVP dependency.
- Raw runtime storage may survive a backend restart, while SQLite indexes remain process-local for the current demo. Startup reconciliation of existing raw files is out of scope unless explicitly added later.
- Batch processing is synchronous and single-process at the current 10,000-record limit.
- Identity bindings are preconfigured from synthetic data rather than discovered from a live directory.

## Out of Scope

- Live AWS, Azure, or GCP authentication, polling, event subscriptions, webhooks, or SDK clients.
- Kafka, cloud queues, background worker services, managed object storage, distributed locks, or exactly-once delivery claims.
- Production retention policies, legal hold, encryption-key management, tenant isolation, authorization, or customer telemetry.
- ZIP/GZIP ingestion, syslog, CEF, OCSF, SIEM forwarding, and providers beyond the three named formats.
- Identity-directory discovery, geolocation enrichment, Isolation Forest training, Context Builder logic, LLM calls, risk scoring, dashboard redesign, and automated response.
- Deleting archived raw batches through an API.
