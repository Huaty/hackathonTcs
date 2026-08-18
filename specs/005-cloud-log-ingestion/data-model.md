# Phase 1 Data Model: Cloud Log Ingestion and Raw Replay

## Design goals

- Preserve exact provider-native bytes before normalized publication.
- Make batch, record, normalization, quarantine, and replay lineage traceable.
- Keep raw payloads separate from feature 004's normalized event table.
- Make duplicate ingestion and same-version replay idempotent.
- Keep storage local and simple while leaving a clean object-store adapter seam.

## Entity relationships

```text
IngestionBatch 1 ─── * RawEventRecord
RawEventRecord 1 ─── * NormalizationAttempt
SourceIdentityBinding * ─── 1 Identity (feature 004)
NormalizationAttempt 0..1 ─── 1 SecurityEvent (feature 004)
NormalizationAttempt 0..1 ─── 1 QuarantineRecord
ReplayRun 1 ─── * NormalizationAttempt
```

## Filesystem layout

The runtime root is configurable and excluded from Git. Client input never supplies path segments.

```text
<RAW_STORE_ROOT>/
└── batches/
    └── <batch-id>/
        ├── original.json
        └── metadata.json
```

Write `original.json.tmp-<generated-token>`, flush/close it, calculate and verify its digest, then atomically rename it to `original.json`. Only after the rename succeeds may the SQLite batch row become `archived`.

`metadata.json` is a convenience sidecar, not the authoritative searchable index. It contains no raw payload copy.

## SQLite schema delta

### `ingestion_batches`

| Column | Type | Rules |
|---|---|---|
| `batch_id` | TEXT PRIMARY KEY | Generated immutable identifier |
| `provider` | TEXT NOT NULL | `aws_cloudtrail`, `azure_activity_log`, `gcp_audit_log` |
| `source_account_id` | TEXT NOT NULL | AWS account, Azure subscription, or GCP project scope |
| `original_filename` | TEXT NOT NULL | Display metadata only; never used as a path |
| `content_type` | TEXT NOT NULL | Validated supported JSON/JSONL type |
| `received_at` | TEXT NOT NULL | ISO-8601 UTC |
| `storage_key` | TEXT NOT NULL UNIQUE | Generated relative key beneath raw root |
| `sha256` | TEXT NOT NULL | Lowercase hex digest of exact uploaded bytes |
| `byte_count` | INTEGER NOT NULL | 0–25 MiB |
| `record_count` | INTEGER NOT NULL | Parsed candidate count; 0 before parsing failure |
| `status` | TEXT NOT NULL | `receiving`, `archived`, `processing`, `completed`, `completed_with_errors`, `rejected` |
| `duplicate_of_batch_id` | TEXT NULL FK | Prior identical provider/source/digest batch |
| `normalized_count` | INTEGER NOT NULL | Request-local successful unique publications |
| `duplicate_count` | INTEGER NOT NULL | Duplicate raw records |
| `quarantined_count` | INTEGER NOT NULL | Failed records |
| `created_at` | TEXT NOT NULL | ISO-8601 UTC |
| `completed_at` | TEXT NULL | ISO-8601 UTC |

Unique index on `(provider, source_account_id, sha256)` identifies duplicate batches.

### `raw_event_records`

| Column | Type | Rules |
|---|---|---|
| `raw_event_id` | TEXT PRIMARY KEY | Deterministic provider/source/native-or-hash identity |
| `batch_id` | TEXT NOT NULL FK | First archived batch containing this raw record |
| `record_index` | INTEGER NOT NULL | Zero-based position in the provider envelope |
| `provider` | TEXT NOT NULL | Closed provider enum |
| `source_account_id` | TEXT NOT NULL | Provider source scope |
| `native_event_id` | TEXT NULL | Native provider ID when available |
| `record_sha256` | TEXT NOT NULL | Digest of canonical JSON record |
| `event_time_utc` | TEXT NULL | Parsed only when valid |
| `status` | TEXT NOT NULL | `pending`, `normalized`, `quarantined` |
| `normalized_event_id` | TEXT NULL | Feature-004 event ID after publication |
| `first_seen_at` | TEXT NOT NULL | ISO-8601 UTC |
| `last_seen_at` | TEXT NOT NULL | Updated on duplicate observation |

Unique index on `(batch_id, record_index)` preserves batch lineage. A separate `raw_event_occurrences` table may record later duplicate batch/index observations without changing first-seen lineage.

### `raw_event_occurrences`

| Column | Type | Rules |
|---|---|---|
| `batch_id` | TEXT NOT NULL FK | Containing batch |
| `record_index` | INTEGER NOT NULL | Position in this occurrence |
| `raw_event_id` | TEXT NOT NULL FK | Resolved stable raw record |
| `observed_at` | TEXT NOT NULL | ISO-8601 UTC |

Primary key `(batch_id, record_index)`.

### `source_identity_bindings`

| Column | Type | Rules |
|---|---|---|
| `binding_id` | TEXT PRIMARY KEY | Stable binding identifier |
| `provider` | TEXT NOT NULL | Closed provider enum |
| `source_account_id` | TEXT NOT NULL | Provider source scope |
| `principal_key` | TEXT NOT NULL | ARN, Azure object ID, or GCP principal email |
| `identity_id` | TEXT NOT NULL FK | Feature-004 stable identity |
| `mapping_version` | TEXT NOT NULL | e.g. `identity-map-v1` |
| `created_at` | TEXT NOT NULL | ISO-8601 UTC |

Unique index on `(provider, source_account_id, principal_key, mapping_version)`.

### `normalization_attempts`

| Column | Type | Rules |
|---|---|---|
| `attempt_id` | TEXT PRIMARY KEY | Deterministic or generated attempt identifier |
| `raw_event_id` | TEXT NOT NULL FK | Raw input |
| `replay_id` | TEXT NULL FK | Null for initial ingestion |
| `normalizer_version` | TEXT NOT NULL | Provider normalizer version |
| `mapping_version` | TEXT NOT NULL | Identity-binding version |
| `status` | TEXT NOT NULL | `normalized`, `duplicate`, `quarantined`, `publication_failed` |
| `normalized_event_id` | TEXT NULL | Feature-004 event ID |
| `normalized_sha256` | TEXT NULL | Canonical normalized-output digest |
| `reason_code` | TEXT NULL | Closed quarantine/failure code |
| `diagnostic` | TEXT NULL | Bounded to 500 characters |
| `created_at` | TEXT NOT NULL | ISO-8601 UTC |

Unique index on `(raw_event_id, normalizer_version, mapping_version)` makes same-input replay idempotent.

### `quarantine_records`

| Column | Type | Rules |
|---|---|---|
| `quarantine_id` | TEXT PRIMARY KEY | Stable record identifier |
| `attempt_id` | TEXT NOT NULL UNIQUE FK | Failed attempt |
| `raw_event_id` | TEXT NOT NULL FK | Raw lineage |
| `reason_code` | TEXT NOT NULL | Closed enum |
| `diagnostic` | TEXT NOT NULL | Bounded non-payload text |
| `created_at` | TEXT NOT NULL | ISO-8601 UTC |

### `replay_runs`

| Column | Type | Rules |
|---|---|---|
| `replay_id` | TEXT PRIMARY KEY | Immutable replay identifier |
| `batch_id` | TEXT NOT NULL FK | Known archived batch |
| `target_normalizer_version` | TEXT NOT NULL | Supported version |
| `mapping_version` | TEXT NOT NULL | Identity bindings used |
| `reason` | TEXT NOT NULL | Required, bounded operator reason |
| `status` | TEXT NOT NULL | `pending`, `running`, `completed`, `completed_with_errors`, `failed` |
| `normalized_count` | INTEGER NOT NULL | New/changed successful outputs |
| `unchanged_count` | INTEGER NOT NULL | Equivalent prior outputs |
| `quarantined_count` | INTEGER NOT NULL | Failed records |
| `affected_event_ids` | TEXT NOT NULL | Validated JSON array for downstream rebuild |
| `created_at` | TEXT NOT NULL | ISO-8601 UTC |
| `completed_at` | TEXT NULL | ISO-8601 UTC |

## Stable identifier algorithms

Use canonical compact JSON with sorted keys and UTF-8 for record/output hashes.

```text
batch digest = SHA256(exact uploaded bytes)

native raw key = provider + "\n" + sourceAccountId + "\n" + nativeEventId
fallback raw key = provider + "\n" + sourceAccountId + "\nsha256:" + recordSha256
rawEventId = "raw-" + first 32 hex characters of SHA256(raw key)

eventId = provider prefix + ":" + sourceAccountId + ":" + nativeEventId
fallback eventId = provider prefix + ":" + sourceAccountId + ":sha256:" + recordSha256
```

Provider prefixes are `aws`, `azure`, and `gcp`. IDs are stable but opaque to clients.

## Provider parsing envelopes

### AWS CloudTrail

```json
{ "Records": [ { "eventVersion": "1.09", "eventID": "..." } ] }
```

Required for normalization: `eventTime`, `eventSource`, `eventName`, resolvable `userIdentity`, and `eventID` or hash fallback.

### Azure Activity Log

```json
{ "records": [ { "eventDataId": "...", "eventTimestamp": "..." } ] }
```

Required for normalization: `eventTimestamp`, `operationName.value`, resolvable claims/caller, and `eventDataId` or hash fallback.

### GCP Audit Log

One JSON object per line.

Required for normalization: `timestamp`, `protoPayload.serviceName`, `protoPayload.methodName`, resolvable `authenticationInfo.principalEmail`, and `insertId` or hash fallback.

## Normalized output shape

Feature 005 publishes feature 004's contract and retains raw lineage separately:

```json
{
  "eventId": "aws:111122223333:aws-evt-0001",
  "identityId": "id-aisha-rahman",
  "eventTimeUtc": "2026-08-18T01:15:00Z",
  "source": {
    "ip": "198.51.100.10",
    "country": null,
    "region": null,
    "city": null,
    "asn": null
  },
  "service": "iam.amazonaws.com",
  "action": "AttachRolePolicy",
  "resource": {
    "type": "AWS::IAM::Role",
    "id": "arn:aws:iam::111122223333:role/demo-ops-role"
  },
  "outcome": "success",
  "sessionId": "aws-session-001"
}
```

## State transitions

```text
Batch: receiving → archived → processing → completed | completed_with_errors
                    └────────────────────→ rejected (parse/limit failure)

Raw record: pending → normalized
                  └→ quarantined

Replay: pending → running → completed | completed_with_errors | failed
```

Raw files and completed batch identity are immutable. New normalizer behavior creates new attempts/replay records rather than rewriting lineage.

## Quarantine reason enum

```text
invalid_json
unsupported_shape
missing_native_fields
invalid_event_time
unresolved_identity
normalization_validation_failed
publication_failed
```

## Synthetic pack model

```text
aws-cloudtrail.json          exact runtime AWS envelope
azure-activity-log.json      exact runtime Azure envelope
gcp-audit-log.jsonl          exact runtime GCP JSONL records
identity-bindings.json       runtime principal → identityId configuration
expected-normalized-events.jsonl
                             test-only raw native ID → expected result/output
manifest.json                generator version/seed/counts/file SHA-256 values
```

Expected results and scenario descriptions MUST never be copied into the provider runtime files or sent to feature 004.
