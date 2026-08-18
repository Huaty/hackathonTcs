# Contract: Raw Cloud-Log Ingestion

## `POST /api/ingestion/batches`

Archives and synchronously processes one provider-native synthetic batch.

### Request

`multipart/form-data` with:

- `file`: required JSON or JSONL file, maximum 25 MiB.

Required query parameters:

- `provider`: `aws_cloudtrail`, `azure_activity_log`, or `gcp_audit_log`.
- `sourceAccountId`: non-empty provider scope; AWS account, Azure subscription, or GCP project identifier.

Optional query parameters:

- `normalizerVersion`: defaults to the current supported version.
- `mappingVersion`: defaults to `identity-map-v1`.

Client filenames are retained as bounded display metadata only. They never control the storage path.

### Response `201 Created`

```json
{
  "batchId": "batch-01J5...",
  "provider": "aws_cloudtrail",
  "sourceAccountId": "111122223333",
  "status": "completed_with_errors",
  "receivedAt": "2026-08-18T04:00:00Z",
  "sha256": "7a...",
  "byteCount": 8421,
  "recordCount": 8,
  "normalizedCount": 5,
  "duplicateCount": 1,
  "quarantinedCount": 2,
  "unresolvedIdentityCount": 1,
  "duplicateOfBatchId": null,
  "normalizerVersion": "cloud-normalizer-v1",
  "mappingVersion": "identity-map-v1",
  "errors": [
    {
      "recordIndex": 6,
      "rawEventId": "raw-...",
      "reasonCode": "unresolved_identity",
      "message": "No identity binding for the provider principal"
    }
  ]
}
```

Errors are capped at 20 and each message at 500 characters. Counts describe this request only.

### Response `200 OK` — duplicate batch

Returns the same shape with `duplicateOfBatchId` set and no new normalized rows. `duplicateCount` equals the candidate record count where the archived prior batch is reused.

### Errors

- `400`: invalid JSON/JSONL, unsupported provider envelope, empty batch, compressed input, no usable records, or unsupported requested version.
- `413`: upload exceeds 25 MiB or parsed candidate count exceeds 10,000.
- `422`: missing file/query fields or invalid request types.
- `500`: raw archive could not be completed. No normalized event is published.

For a syntactically unreadable but successfully archived file, the error body MAY include a `batchId` with `status=rejected`; it must explicitly state that the raw batch exists. An archive failure never returns an indexed completed batch.

## `GET /api/ingestion/batches/{batchId}`

Returns batch metadata and record lineage. Raw payload content is not returned by this endpoint.

Optional query parameters:

- `recordLimit`: integer 1–100, default 100.
- `recordOffset`: non-negative integer, default 0.

### Response `200 OK`

```json
{
  "batch": {
    "batchId": "batch-01J5...",
    "provider": "aws_cloudtrail",
    "sourceAccountId": "111122223333",
    "originalFilename": "aws-cloudtrail.json",
    "receivedAt": "2026-08-18T04:00:00Z",
    "sha256": "7a...",
    "byteCount": 8421,
    "recordCount": 8,
    "status": "completed_with_errors",
    "normalizedCount": 5,
    "duplicateCount": 1,
    "quarantinedCount": 2
  },
  "records": [
    {
      "recordIndex": 0,
      "rawEventId": "raw-...",
      "nativeEventId": "aws-evt-0001",
      "eventTimeUtc": "2026-08-18T01:15:00Z",
      "status": "normalized",
      "normalizedEventId": "aws:111122223333:aws-evt-0001",
      "normalizerVersion": "cloud-normalizer-v1",
      "reasonCode": null
    }
  ]
}
```

### Errors

- `404`: batch ID does not exist.

## Provider envelope rules

- AWS accepts a JSON object containing a non-empty `Records` array.
- Azure accepts a JSON object containing a non-empty `records` array.
- GCP accepts non-empty JSONL with one object per line.
- Array roots and generic `{events: [...]}` envelopes are not accepted by this raw-provider endpoint.
