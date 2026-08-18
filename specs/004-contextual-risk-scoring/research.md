# Phase 0 Research: Policy-First AI Contextual Risk Scoring

## 1. Score composition

**Decision**: Policies produce the authoritative 0–100 base score. AI returns one bounded contextual adjustment. The server performs the final arithmetic and applies policy severity floors after AI.

```text
policyScore = min(100, context points + highest action points + highest compound/sequence points)
preFloorScore = clamp(policyScore + aiAdjustmentApplied, 0, 100)
finalRiskScore = max(preFloorScore, severityFloorMinimum)
```

**Rationale**: Averaging two independent 0–100 scores would let AI erase strong rules and double-count the same evidence. A bounded adjustment expresses context without transferring authority over rules or arithmetic.

**Alternatives rejected**:
- Isolation Forest plus security context: superseded by project-owner direction.
- AI-generated final score: too variable and difficult to audit.
- Weighted average of policy and AI scores: lets low AI output suppress high-confidence policy evidence.

## 2. AI adjustment rubric

**Decision**: Valid adjustments are `-15`, `-5`, `0`, `10`, `20`, and `25`.

| Adjustment | Meaning |
|---:|---|
| -15 | Strong, evidenced approved/expected context materially reduces concern |
| -5 | Some specific mitigating context |
| 0 | No reliable additional context or AI unavailable/invalid |
| +10 | Multiple concerning facts form a meaningful sequence |
| +20 | Likely attack progression or substantial blast radius |
| +25 | Very strong evidence of active compromise |

Confidence below 0.60 applies zero. Positive adjustments require valid evidence event IDs. Negative adjustments additionally require a concrete mitigating factor. Policy floors always win.

## 3. Policy aggregation and double counting

**Decision**: All matching context rules add. Only the highest action rule and highest compound/sequence rule add. The total is capped at 100.

**Rationale**: Location, time, service, and frequency are independent deviations. Action rules are mutually ranked descriptions of one action, and compound rules are escalation bonuses; selecting the highest in those groups prevents accidental stacking.

## 4. Severity floors

**Decision**: `POL-DISABLE-PROTECTION` and `POL-NEW-LOCATION-ADMIN` impose High (minimum 65). `POL-PROTECTION-AFTER-PRIVILEGE` imposes Critical (minimum 85). Floors are calculated from matched enabled rules and applied after AI.

**Rationale**: A negative or unavailable AI assessment must not downgrade deterministic evidence of protection tampering or a confirmed dangerous sequence below the organization's minimum response level.

## 5. AI prompt boundary

**Decision**: The prompt contains a fixed system rubric plus a JSON data block containing the event, at most 20 correlated events from the preceding 60 minutes, identity/baseline summary, and immutable policy results. Raw log strings are labelled untrusted. The response uses a strict Pydantic schema.

**Rationale**: This gives the model enough sequence and business context without allowing log-controlled text to redefine instructions or policy results.

## 6. AI failure behavior

**Decision**: Transport error, timeout, malformed response, unsupported adjustment, low confidence, invalid evidence IDs, positive adjustment without evidence, or negative adjustment without mitigation produces `aiAdjustmentApplied = 0`. The response records a precise status such as `applied`, `unavailable`, `invalid`, or `low_confidence`.

**Rationale**: Policy-only evaluation remains complete and usable. Returning an assessment rather than a 5xx makes degradation explicit and demo-safe.

## 7. AI caching and idempotency

**Decision**: Cache AI context by event ID, baseline version, policy snapshot version, prompt version, and model. Equivalent requests return the same assessment. A forced refresh creates a new versioned AI decision and therefore a new assessment; it never mutates prior results.

## 8. Policy representation

**Decision**: Policies use approved `condition_key` enums implemented by code. Database rows hold identity, display, points, floor, enabled state, and version. They do not contain arbitrary Python, SQL, or expression-language code.

**Rationale**: Operators can safely toggle explicit controls without creating a remote-code or policy-injection surface.

## 9. Identity baseline and sequence scope

**Decision**: Retain the approved 30-day baseline, 15-minute frequency window, historical p95, and 20 events/7 active days confidence threshold. AI and sequence policies receive at most 20 prior events from the same identity/session within 60 minutes.

## 10. Synthetic packaging

**Decision**: Use five files:

```text
identities.json
baseline-events.jsonl
evaluation-events.jsonl
mock-ai-decisions.json
expected-assessments.json
```

Mock AI decisions and expected results are test-only and never included in runtime event payloads or production prompts.

## 11. Existing partial implementation

**Decision**: Stable identity, event, and baseline work already started may be retained after review. Isolation Forest fields, weighted context formula, action-classification-as-AI-authority, and their tests are superseded and must be replaced before implementation resumes.

## Outstanding NEEDS CLARIFICATION

None. The project owner explicitly requested the policy-plus-AI model on 2026-08-18 and asked for the Spec Kit artifacts to be updated using the proposed bounded-adjustment design.
