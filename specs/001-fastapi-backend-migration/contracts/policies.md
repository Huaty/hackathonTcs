# Contract: Policies

Covers FR-008.

## `GET /api/policies`

**Response 200**:
```json
{ "policies": [ /* PolicyRule[], see data-model.md */ ] }
```

## `POST /api/policies/{title}/toggle`

Flips a policy's `enabled` state. `title` is used as the identifier
(matches the existing seed data, which has no separate numeric id).

**Request body**: none.

**Response 200**: the updated `PolicyRule` object.

**Response 404**: `{ "detail": "Policy '{title}' not found" }` if unknown.
