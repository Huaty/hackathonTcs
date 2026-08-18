# Phase 1 Data Model: Policy-First AI Contextual Risk Scoring

## Relationships

```text
Identity 1 ─── * SecurityEvent
Identity 1 ─── * IdentityBaseline
PolicyRule * ─── * PolicySnapshot
SecurityEvent 1 ─── * PolicyEvaluation
PolicyEvaluation 1 ─── 1 AIContextDecision
PolicyEvaluation + AIContextDecision 1 ─── 1 RiskAssessment
RiskAssessment 0..1 ─── 1 Finding
```

## Existing identity/event foundation

Retain the revised stable-ID structures from the prior plan:

- `identities.identity_id` is authoritative; display/principal names are attributes.
- `security_events.event_id` is immutable and idempotent.
- `identity_baselines` stores append-only 30-day snapshots with confidence and unknown fields.
- Legacy identity/activity response fields remain compatibility projections.

## Policy Rule (`policies`, evolved existing table)

| Column | Type | Meaning |
|---|---|---|
| `rule_id` | TEXT PRIMARY KEY | Stable Policy Catalog v1 ID |
| `title` | TEXT NOT NULL | Existing UI field |
| `description` | TEXT NOT NULL | Existing UI field |
| `category` | TEXT NOT NULL | `context`, `action`, or `compound_sequence` |
| `condition_key` | TEXT NOT NULL | Approved non-executable enum implemented in code |
| `points` | INTEGER NOT NULL | 0–100 contribution |
| `severity_floor` | TEXT NULL | `High`, `Critical`, or null |
| `enabled` | INTEGER NOT NULL | Existing toggle behavior |
| `policy_version` | TEXT NOT NULL | `policy-catalog-v1` initially |
| `updated_at` | TEXT NOT NULL | UTC timestamp |

No row contains executable Python, SQL, or expression-language content.

## Policy Snapshot

An immutable JSON snapshot stored per evaluation:

```json
{
  "policyVersion": "policy-catalog-v1",
  "rules": [
    {
      "ruleId": "POL-NEW-SOURCE",
      "category": "context",
      "conditionKey": "new_source_or_location",
      "points": 20,
      "severityFloor": null,
      "enabled": true
    }
  ]
}
```

Snapshot hash/version participates in idempotency. Policy toggles create a different snapshot for future assessments; historical snapshots do not change.

## Policy Rule Result

```text
ruleId
category
state: matched | not_matched | unknown | disabled
configuredPoints
awardedPoints
severityFloor
evidence
evidenceEventIds[]
```

Context results all contribute when matched. The policy engine selects the highest awarded action result and highest awarded compound/sequence result; other matched rules remain visible with `selected=false` and award zero to prevent double counting.

## Policy Evaluation (`policy_evaluations`)

| Column | Type | Meaning |
|---|---|---|
| `policy_evaluation_id` | TEXT PRIMARY KEY | Deterministic versioned ID |
| `event_id` | TEXT FK | Target event |
| `baseline_id` | TEXT FK | Exact baseline evidence |
| `policy_version` | TEXT NOT NULL | Catalog version |
| `policy_snapshot` | TEXT NOT NULL | Immutable validated JSON |
| `rule_results` | TEXT NOT NULL | Immutable validated JSON array |
| `policy_score` | INTEGER NOT NULL | Capped 0–100 base score |
| `severity_floor` | TEXT NULL | Strongest matched enabled floor |
| `severity_floor_minimum` | INTEGER NOT NULL | 0, 65, or 85 |
| `created_at` | TEXT NOT NULL | UTC |

Unique key: `(event_id, baseline_id, policy_snapshot_hash)`.

## AI Context Decision (`ai_context_decisions`)

| Column | Type | Meaning |
|---|---|---|
| `ai_decision_id` | TEXT PRIMARY KEY | Deterministic cache/version ID |
| `event_id` | TEXT FK | Target event |
| `policy_evaluation_id` | TEXT FK | Immutable policy input |
| `adjustment_requested` | INTEGER NULL | Raw validated enum when parseable |
| `adjustment_applied` | INTEGER NOT NULL | Approved adjustment or zero |
| `confidence` | REAL NULL | 0–1 when parseable |
| `status` | TEXT NOT NULL | `applied`, `zero`, `low_confidence`, `invalid`, `unavailable` |
| `risk_factors` | TEXT NOT NULL | JSON array |
| `mitigating_factors` | TEXT NOT NULL | JSON array |
| `evidence_event_ids` | TEXT NOT NULL | JSON array validated against prompt context |
| `explanation` | TEXT NOT NULL | Plain-language context/fallback explanation |
| `validation_errors` | TEXT NOT NULL | JSON array |
| `model` | TEXT NULL | Proxy model alias |
| `prompt_version` | TEXT NOT NULL | `risk-context-prompt-v1` |
| `created_at` | TEXT NOT NULL | UTC |

Cache/idempotency identity includes event, baseline, policy snapshot, model, prompt version, and validated decision. A force refresh creates a new decision; it never overwrites the previous row.

## Risk Assessment (`risk_assessments`)

| Column | Type | Meaning |
|---|---|---|
| `assessment_id` | TEXT PRIMARY KEY | Deterministic versioned ID |
| `event_id` | TEXT FK | Target event |
| `policy_evaluation_id` | TEXT FK | Exact policy input/result |
| `ai_decision_id` | TEXT FK | Exact AI/fallback result |
| `policy_score` | INTEGER NOT NULL | Copied immutable base score |
| `ai_adjustment_applied` | INTEGER NOT NULL | Copied bounded adjustment |
| `pre_floor_score` | INTEGER NOT NULL | Clamped base + adjustment |
| `severity_floor` | TEXT NULL | Strongest floor |
| `severity_floor_minimum` | INTEGER NOT NULL | 0/65/85 |
| `final_risk_score` | INTEGER NOT NULL | Post-floor 0–100 |
| `severity` | TEXT NOT NULL | Low/Medium/High/Critical |
| `scoring_version` | TEXT NOT NULL | `policy-ai-risk-v1` |
| `created_at` | TEXT NOT NULL | UTC |

Unique key: `(event_id, policy_evaluation_id, ai_decision_id, scoring_version)`.

## AI response schema

```json
{
  "adjustment": 10,
  "confidence": 0.88,
  "riskFactors": ["Permission change followed a new-country login"],
  "mitigatingFactors": [],
  "evidenceEventIds": ["EVT-104", "EVT-105"],
  "explanation": "The correlated sequence resembles a privilege pivot."
}
```

Validation invariants:

1. Adjustment is one of `-15,-5,0,10,20,25`.
2. Confidence is 0–1 and must be at least 0.60 for a nonzero applied adjustment.
3. Every evidence ID exists in the bounded prompt context.
4. Positive adjustment requires evidence.
5. Negative adjustment requires mitigation.
6. Any failure produces applied adjustment zero and explicit status/errors.

## Calculation invariants

```text
contextPoints = sum(all selected matched context rules)
actionPoints = max(selected matched action rule, default 0)
compoundPoints = max(selected matched compound/sequence rule, default 0)
policyScore = min(100, contextPoints + actionPoints + compoundPoints)
preFloorScore = clamp(policyScore + aiAdjustmentApplied, 0, 100)
finalRiskScore = max(preFloorScore, severityFloorMinimum)
```

Severity:

```text
0–39 Low | 40–64 Medium | 65–84 High | 85–100 Critical
```

## Synthetic pack

```text
datasets/risk-scoring/identities.json             runtime input
datasets/risk-scoring/baseline-events.jsonl       runtime input
datasets/risk-scoring/evaluation-events.jsonl     runtime input
datasets/risk-scoring/mock-ai-decisions.json      test-only mocked provider output
datasets/risk-scoring/expected-assessments.json   test-only oracle
```

Mock decisions and expected results MUST NOT be stored in `security_events.raw_payload` or sent as runtime prompt context.

## Superseded fields

The following partial-design fields are removed rather than deprecated:

- `isolation_forest_score`
- `baseline_deviation_score` as a separately weighted score
- `action_sensitivity_score` as an AI-controlled input
- `compound_risk_score` in the former weighted formula
- `security_context_score`

Their underlying facts remain represented as explicit Policy Catalog rule results.
