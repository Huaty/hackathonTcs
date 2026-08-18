# Contract: Configuration

Covers FR-010.

## `GET /api/configuration`

**Response 200**:
```json
{ "notificationsEnabled": true, "plainLanguageExplanations": true }
```

## `PUT /api/configuration`

**Request body**: full `Configuration` object (replace, not patch — matches
current "Save preferences" single-action UX).
```json
{ "notificationsEnabled": true, "plainLanguageExplanations": false }
```

**Response 200**: the saved `Configuration` object (echoed back).

**Response 422**: missing/invalid fields (FastAPI default validation error).
