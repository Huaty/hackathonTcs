# Contract: Identity Profiles

Covers FR-006.

## `GET /api/identities`

**Response 200**:
```json
{ "identities": [ /* Identity[], see data-model.md */ ] }
```

## `GET /api/identities/{name}/timeline`

Returns the activity timeline for one identity, derived by filtering
`activity_log`/`findings` where `actor`/`entity` matches `name`.

- **200**: `{ "events": [ /* ActivityEvent[] */ ] }`
- **404**: unknown identity `name`.
