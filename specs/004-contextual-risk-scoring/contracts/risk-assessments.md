# Contract: Policy + AI Risk Assessments

## `POST /api/risk-assessments`

Assesses one already-stored event using the current immutable policy snapshot and bounded AI context.

**Request**:

```json
{
  "eventId": "EVT-104",
  "forceAiRefresh": false
}
```

**Response 200/201**:

```json
{
  "assessmentId": "risk-EVT-104-policy-ai-v1",
  "eventId": "EVT-104",
  "baseline": {
    "baselineId": "base-aisha-20260818",
    "confidence": "high"
  },
  "policyEvaluation": {
    "policyEvaluationId": "policy-eval-EVT-104-v1",
    "policyVersion": "policy-catalog-v1",
    "policyScore": 75,
    "severityFloor": "High",
    "severityFloorMinimum": 65,
    "ruleResults": [
      {
        "ruleId": "POL-NEW-SOURCE",
        "category": "context",
        "state": "matched",
        "selected": true,
        "configuredPoints": 20,
        "awardedPoints": 20,
        "severityFloor": null,
        "evidence": "Location DE was absent from the established 30-day baseline.",
        "evidenceEventIds": ["EVT-104"]
      },
      {
        "ruleId": "POL-PERMISSION-CHANGE",
        "category": "action",
        "state": "matched",
        "selected": true,
        "configuredPoints": 35,
        "awardedPoints": 35,
        "severityFloor": null,
        "evidence": "AttachAdminPolicy changes effective administrator permissions.",
        "evidenceEventIds": ["EVT-104"]
      },
      {
        "ruleId": "POL-NEW-LOCATION-ADMIN",
        "category": "compound_sequence",
        "state": "matched",
        "selected": true,
        "configuredPoints": 20,
        "awardedPoints": 20,
        "severityFloor": "High",
        "evidence": "A new location and administrator change occurred together.",
        "evidenceEventIds": ["EVT-104"]
      }
    ]
  },
  "aiContext": {
    "status": "applied",
    "adjustmentRequested": 10,
    "adjustmentApplied": 10,
    "confidence": 0.88,
    "riskFactors": ["New-country login immediately preceded a privilege pivot"],
    "mitigatingFactors": [],
    "evidenceEventIds": ["EVT-103", "EVT-104"],
    "explanation": "The correlated sequence resembles a privilege pivot.",
    "validationErrors": [],
    "model": "genailab-maas-Opus-4.6",
    "promptVersion": "risk-context-prompt-v1"
  },
  "calculation": {
    "policyScore": 75,
    "aiAdjustmentApplied": 10,
    "preFloorScore": 85,
    "severityFloorMinimum": 65,
    "finalRiskScore": 85
  },
  "severity": "Critical",
  "scoringVersion": "policy-ai-risk-v1",
  "createdAt": "2026-08-18T09:00:00Z"
}
```

**Response semantics**:

- `201` when a new assessment is stored.
- `200` when the equivalent versioned assessment already exists.
- AI timeout/invalid/low-confidence paths still return a successful policy assessment with adjustment zero and explicit `aiContext.status`.
- `forceAiRefresh=true` requests a new AI decision; it does not mutate prior rows.

**Response 404**: event does not exist.

**Response 409**: stable identity or required baseline/policy prerequisite cannot be resolved. AI failure alone is never a 409.

## `GET /api/risk-assessments/{assessmentId}`

Returns the same immutable breakdown. `404` when absent.

## `GET /api/events/{eventId}/risk-assessments`

Returns assessments newest first, preserving policy/prompt/model revisions.

## Calculation contract

```text
policyScore = min(100, context + highest action + highest compound/sequence)
validated adjustment ∈ {-15,-5,0,10,20,25}; otherwise applied adjustment = 0
preFloorScore = clamp(policyScore + aiAdjustmentApplied, 0, 100)
finalRiskScore = max(preFloorScore, severityFloorMinimum)

0–39 Low | 40–64 Medium | 65–84 High | 85–100 Critical
```

The AI cannot change rule states, points, floors, thresholds, or arithmetic.
