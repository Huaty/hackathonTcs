# Contract: Raw Batch Replay

## `POST /api/ingestion/replays`

Synchronously reprocesses one known archived batch using an explicitly supported normalizer and identity-mapping version.

### Request

```json
{
  "batchId": "batch-01J5...",
  "targetNormalizerVersion": "cloud-normalizer-v1",
  "mappingVersion": "identity-map-v1",
  "reason": "Verify deterministic replay after parser fix"
}
```

`reason` is required, trimmed, and limited to 200 characters.

### Response `201 Created`

```json
{
  "replayId": "replay-01J5...",
  "batchId": "batch-01J5...",
  "status": "completed_with_errors",
  "targetNormalizerVersion": "cloud-normalizer-v1",
  "mappingVersion": "identity-map-v1",
  "recordCount": 8,
  "normalizedCount": 0,
  "unchangedCount": 6,
  "quarantinedCount": 2,
  "affectedEventIds": [],
  "createdAt": "2026-08-18T05:00:00Z",
  "completedAt": "2026-08-18T05:00:01Z",
  "errors": []
}
```

### Response `200 OK` — equivalent replay

If an equivalent completed replay already exists for the same batch, normalizer version, mapping version, and archived digest, the prior result may be returned with `200` rather than creating a duplicate run.

### Errors

- `400`: unsupported normalizer/mapping version or invalid reason.
- `404`: batch does not exist or archived file is missing.
- `409`: batch is not in a replayable archived/completed state, or archived digest no longer matches the index.
- `422`: invalid request shape.
- `500`: replay orchestration failure; existing normalized events and assessments remain unchanged.

## `GET /api/ingestion/replays/{replayId}`

Returns the same complete replay result plus bounded per-record errors.

- `200`: replay exists.
- `404`: replay does not exist.

## Replay invariants

1. The archived batch is opened only through its stored generated key beneath the configured raw root.
2. Its exact-byte SHA-256 must match the batch index before parsing.
3. Existing same-version successful attempts are counted as unchanged rather than republished.
4. New normalized output validates before publication.
5. Changed successful outputs return affected event IDs for a separate feature-004 context rebuild.
6. Existing risk assessments are never overwritten or recomputed by this endpoint.
7. Replay never calls liteLLM or any other model endpoint.
