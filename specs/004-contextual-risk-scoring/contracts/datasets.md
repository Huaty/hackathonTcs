# Contract: Rich Identity and Security-Event Import

Extends `POST /api/datasets` while preserving `acceptedCount`, `rejectedCount`, and `errors`.

## `POST /api/datasets?mode=identities`

Imports/upserts identity directory records by stable `identityId`.

**Response 200**:

```json
{
  "acceptedCount": 20,
  "rejectedCount": 0,
  "errors": [],
  "duplicateCount": 0,
  "identitiesCreated": 18,
  "identitiesUpdated": 2,
  "eventsStored": 0
}
```

Display-name changes do not create a second identity.

## `POST /api/datasets?mode=events`

Imports normalized CSV, JSON, or JSONL events with `eventId`, `identityId`, full UTC timestamp, source, service, action, resource, outcome, and optional session/correlation ID.

**Response 200**:

```json
{
  "acceptedCount": 96,
  "rejectedCount": 2,
  "errors": ["Row 17: identityId 'id-missing' was not found"],
  "duplicateCount": 4,
  "identitiesCreated": 0,
  "identitiesUpdated": 0,
  "eventsStored": 92
}
```

**Behavior**:

- Accepted writes are transactional.
- Duplicate `eventId` values are counted but not inserted again.
- Unresolved identities are rejected/quarantined and never name-guessed.
- Imported events appear in the database-backed profile immediately.
- Import does not automatically call AI for every row. An operator assesses selected evaluation events through `POST /api/risk-assessments`.
- Existing legacy flat aliases remain accepted for Activity Explorer compatibility, but records without a resolvable stable identity are not eligible for risk assessment.

**Response 400**: malformed file, unsupported mode, over 10,000 candidate records, or no usable records; nothing is committed.

**Response 422**: missing file or invalid request envelope.

No Isolation Forest score, expected policy match, AI answer, scenario label, or final score is accepted in runtime event input.
