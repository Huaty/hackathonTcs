# Contract: Database-Backed Identity Profiles

## `GET /api/identities`

Returns existing identity-card fields plus stable/additive profile fields.

**Response 200**:

```json
{
  "identities": [
    {
      "identityId": "id-aisha-rahman",
      "name": "Aisha Rahman",
      "initials": "AR",
      "role": "Cloud Engineer",
      "identityType": "human",
      "status": "active",
      "activity": "Administrator permission change from a new location",
      "score": 85,
      "color": "#ff5962",
      "description": "Usually active 08:00–19:00 Asia/Singapore on AWS IAM and GitHub Enterprise.",
      "baselineConfidence": "high",
      "lastSeenAt": "2026-08-18T08:42:13Z"
    }
  ]
}
```

`name`, `initials`, `role`, `activity`, `score`, `color`, and `description` remain for existing clients.

## `GET /api/identities/{identityId}`

Returns the database-backed profile, latest baseline snapshot, recent events, and latest policy + AI assessments.

Optional query parameters:

- `eventLimit`: integer 1–100, default 25.
- `assessmentLimit`: integer 1–100, default 10.

**Response 200**:

```json
{
  "identity": {
    "identityId": "id-aisha-rahman",
    "name": "Aisha Rahman",
    "identityType": "human",
    "role": "Cloud Engineer",
    "status": "active",
    "homeTimezone": "Asia/Singapore"
  },
  "baseline": {
    "baselineId": "base-aisha-20260818",
    "windowStartUtc": "2026-07-19T00:00:00Z",
    "windowEndUtc": "2026-08-18T08:42:13Z",
    "usualHours": [{ "start": "08:00", "end": "19:00" }],
    "usualSourceIps": ["198.51.100.18"],
    "usualLocations": ["SG"],
    "usualServices": ["AWS IAM", "GitHub Enterprise"],
    "usualActions": ["ConsoleLogin", "ListRoles"],
    "sampleCount": 224,
    "activeDayCount": 24,
    "confidence": "high",
    "unknownFields": []
  },
  "events": [],
  "assessments": [],
  "riskSummary": {
    "latestPolicyScore": 75,
    "latestAiAdjustment": 10,
    "latestAiStatus": "applied",
    "latestSeverityFloor": "High",
    "latestFinalRiskScore": 85,
    "matchedPolicyIds": [
      "POL-NEW-SOURCE",
      "POL-PERMISSION-CHANGE",
      "POL-NEW-LOCATION-ADMIN"
    ]
  }
}
```

Each item in `assessments` uses the immutable response shape from `risk-assessments.md`; profiles do not recompute old assessments from current policy configuration.

**Response 404**: identity ID does not exist.

## Compatibility timeline

`GET /api/identities/{identityId}/timeline` remains available and returns the existing `{ "events": [...] }` envelope, but lookup is by stable ID. During one documented compatibility release, a legacy display-name match MAY be accepted only when it resolves uniquely; the response should expose a deprecation indication and implementation tests must prevent ambiguous matches.
