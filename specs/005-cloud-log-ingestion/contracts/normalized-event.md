# Contract: Normalized Cloud Event Publication

This is the internal boundary from feature 005 to feature 004. It is not a second public event-ingestion endpoint.

## `NormalizedSecurityEventV1`

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

## Field rules

| Field | Rule |
|---|---|
| `eventId` | Deterministic provider/source/native-ID key; hash fallback only when native ID is absent |
| `identityId` | Required stable feature-004 ID resolved through a versioned binding |
| `eventTimeUtc` | Required full ISO-8601 UTC timestamp |
| `source.ip` | Valid IP or null; never invented |
| `source.country/region/city/asn` | Null unless present in trusted source/enrichment; v1 performs no external enrichment |
| `service` | Required native provider service/resource-provider name |
| `action` | Required native method/operation name; do not translate into risk labels |
| `resource.type` | Provider-native resource type when derivable, otherwise null |
| `resource.id` | Provider-native fictitious resource identifier when present, otherwise null |
| `outcome` | `success`, `failure`, or `denied`; deterministic provider mapping |
| `sessionId` | Provider session/correlation/operation ID when available, otherwise null |

## Publication semantics

- Feature 005 validates this model before calling the feature-004 storage method.
- Feature 004 upserts/returns idempotently by `eventId` as defined in its contracts.
- Feature 005 records `rawEventId → eventId` only after publication succeeds.
- A publication conflict caused by different normalized content for the same `eventId` is not silently overwritten; it becomes `publication_failed` until a versioned replay/publish decision is made.
- Raw payload, anomaly labels, expected scores, provider credentials, and normalization diagnostics are forbidden in this object.

## Identity-binding fixture

`identity-bindings.json` uses:

```json
{
  "mappingVersion": "identity-map-v1",
  "bindings": [
    {
      "provider": "aws_cloudtrail",
      "sourceAccountId": "111122223333",
      "principalKey": "arn:aws:iam::111122223333:user/aisha.rahman",
      "identityId": "id-aisha-rahman"
    }
  ]
}
```

Duplicate binding keys within one version or a binding to a missing feature-004 identity fail fixture/configuration loading.
