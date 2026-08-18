# Feature Specification: Policy-First AI Contextual Risk Scoring

**Feature Branch**: `004-contextual-risk-scoring`

**Created**: 2026-08-18

**Revised**: 2026-08-18

**Status**: Approved — revised policy-first scoring model ready for implementation

**Input**: User description: "Risk score = AI prompts we decide + policies/rules. Policies should provide transparent security rules, while AI evaluates broader context. Identity Profiles must use database-backed identities, events, and baselines, and the demo needs realistic synthetic logs."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Receive an explainable policy-first risk score (Priority: P1)

A security analyst reviews an event and sees a deterministic policy base score, every matched rule, the AI contextual adjustment, any severity floor, the final score, and a plain-language explanation supported by real event IDs.

**Why this priority**: This is the core product decision. Policies provide reproducibility; the bounded AI adjustment recognizes sequences, blast radius, and mitigating business context that isolated rules cannot fully express.

**Independent Test**: Submit a stored normalized event with an established identity baseline, independently calculate the policy base score, provide a mocked validated AI response, and confirm the final score and severity exactly match the documented formula.

**Acceptance Scenarios**:

1. **Given** a normal read-only event matching the baseline, **When** it is assessed, **Then** no risk policy adds points, the AI adjustment is zero unless supported by additional evidence, and the response explains the low score.
2. **Given** a new location, administrator-permission change, and high-confidence AI evidence of a privilege-pivot sequence, **When** it is assessed, **Then** the response shows each matched rule, the bounded positive AI adjustment, the applied severity floor, and the deterministic final calculation.
3. **Given** strong policy evidence and an AI response attempting to lower the score, **When** a policy severity floor applies, **Then** the final score cannot fall below that floor.
4. **Given** identical versioned policy evaluation and validated AI context, **When** assessment is repeated, **Then** the returned calculation is idempotent and numerically identical.

---

### User Story 2 - Continue scoring when AI is unavailable or unsafe (Priority: P1)

An analyst still receives a complete policy-based assessment when the AI proxy times out, returns malformed data, lacks confidence, cites nonexistent evidence, or follows instruction-like text embedded in a log.

**Why this priority**: The AI service must improve context without becoming a single point of failure or an authority capable of bypassing deterministic protections.

**Independent Test**: Run the same event through timeout, malformed JSON, unsupported adjustment, low-confidence, nonexistent-evidence, and prompt-injection-like cases; confirm each uses adjustment zero and retains the same policy score/floor.

**Acceptance Scenarios**:

1. **Given** the AI service is unavailable, **When** assessment runs, **Then** `aiAdjustmentApplied` is zero, `aiStatus` is `unavailable`, and final scoring succeeds from policies.
2. **Given** an AI response outside the approved adjustment set, **When** it is validated, **Then** it is rejected and cannot affect any number or severity.
3. **Given** AI confidence below 0.60, **When** assessment runs, **Then** the response may retain the narrative as untrusted diagnostic context but applies adjustment zero.
4. **Given** an event string containing instructions to ignore policy rules, **When** it is sent for context analysis, **Then** the string is treated as untrusted evidence and cannot alter the response schema, rule results, or allowed adjustment.

---

### User Story 3 - Build identity context from stored telemetry (Priority: P1)

An analyst opens Identity Profiles after importing telemetry and sees identities, recent events, baseline behavior, policy assessments, AI context, and current risk derived from stored database records rather than disconnected frontend fixtures.

**Why this priority**: Both rules and AI need reliable identity context. Display-name joins and static prose baselines cannot support trustworthy scoring.

**Independent Test**: Import a new synthetic identity and events, assess one event, and retrieve that identity's profile without editing seed fixtures or restarting the backend.

**Acceptance Scenarios**:

1. **Given** an event with a known `identityId`, **When** it is ingested, **Then** it appears in the correct database-backed timeline.
2. **Given** a valid new identity record and events, **When** they are ingested, **Then** a retrievable profile, baseline, policy result, and assessment can be created.
3. **Given** display-name or case differences for one stable `identityId`, **When** events are ingested, **Then** they remain attached to one identity.
4. **Given** insufficient history, **When** scoring runs, **Then** baseline-dependent rules report `unknown`, add no hidden points, and expose low baseline confidence to AI and the analyst.

---

### User Story 4 - Operate explicit versioned security policies (Priority: P2)

A demo operator can view and enable/disable the approved scoring rules. Each assessment records the exact policy version and rule results used, so later configuration changes do not rewrite historical scores.

**Why this priority**: A policy-based score is only transparent if the rules, points, floors, enabled state, and version are explicit and auditable.

**Independent Test**: Disable one policy, assess a matching event, confirm the rule is reported as disabled and adds zero; re-enable it and create a new assessment that uses the new policy snapshot without changing the prior assessment.

**Acceptance Scenarios**:

1. **Given** an enabled rule whose condition matches, **When** scoring runs, **Then** its configured points and severity floor participate in policy evaluation.
2. **Given** the same rule disabled, **When** scoring runs, **Then** it adds zero and is marked disabled rather than silently omitted.
3. **Given** policy configuration changes after an assessment, **When** the historical assessment is read, **Then** its stored rule version/results remain unchanged.

---

### User Story 5 - Demonstrate the model with realistic synthetic telemetry (Priority: P2)

A demo operator imports separate identity, normal-history, and evaluation-event files that exercise every policy rule, AI adjustment, floor, failure path, severity boundary, and identity-resolution condition without exposing real data or leaking expected labels into prompts.

**Why this priority**: A credible demo requires normal history and controlled scenarios, not only prewritten alert cards.

**Independent Test**: Generate/import the telemetry pack from fresh state and compare actual results with a separate test-only oracle.

**Acceptance Scenarios**:

1. **Given** 30 days of normal history, **When** baselines are built, **Then** established identities receive expected usual hours, locations, services, actions, frequency, and confidence.
2. **Given** evaluation events, **When** they are assessed using mocked AI responses, **Then** every policy condition, allowed AI adjustment, floor, and severity boundary has at least one expected case.
3. **Given** the runtime files, **When** inspected or prompted, **Then** they contain no expected labels, real credentials, real people, or production identifiers.

### Edge Cases

- Policy points are capped at 100 before AI adjustment.
- All matching context policies contribute points; only the highest matching action rule and highest matching compound/sequence rule contribute, preventing same-category double counting.
- AI adjustments are restricted to `-15`, `-5`, `0`, `10`, `20`, or `25`.
- AI confidence below `0.60` results in applied adjustment `0`.
- Positive AI adjustments require at least one evidence event ID that exists in the assessment context.
- Negative AI adjustments require at least one specific mitigating factor and cannot bypass a policy severity floor.
- If AI is unavailable, invalid, or unsafe, policy scoring completes with adjustment `0`.
- Severity floors are applied after AI adjustment; High maps to minimum score 65 and Critical to minimum score 85.
- Missing or low-confidence baseline fields are `unknown`, add zero points, and remain visible.
- Duplicate event ingestion and equivalent assessment requests are idempotent.
- Out-of-order events do not retroactively rewrite the versioned baseline/policy/AI evidence of completed assessments.
- Raw log fields are untrusted prompt data and cannot supply instructions or expected answers.

## Requirements *(mandatory)*

### Policy Catalog v1

Context rules are additive when enabled and matched:

| Rule ID | Condition | Points | Floor |
|---|---|---:|---|
| `POL-NEW-SOURCE` | Source IP or location absent from established baseline | 20 | None |
| `POL-UNUSUAL-TIME` | Event outside normal local activity hours | 10 | None |
| `POL-NEW-SERVICE-ACTION` | Service or action absent from established baseline | 15 | None |
| `POL-HIGH-FREQUENCY` | 15-minute identity/service count exceeds historical p95 | 15 | None |

Exactly the highest matching enabled action rule contributes:

| Rule ID | Condition | Points | Floor |
|---|---|---:|---|
| `POL-READ-ONLY` | Normal read-only action | 0 | None |
| `POL-LOGIN-KEY-CHANGE` | Access-key lifecycle or login-security change | 20 | None |
| `POL-PERMISSION-CHANGE` | Permission, role, privilege, or administrator change | 35 | None |
| `POL-SECRET-ACCESS` | Secret, credential, or protected-key access/change | 40 | None |
| `POL-DISABLE-PROTECTION` | Disable logging/auditing or remove a security protection | 70 | High |

Exactly the highest matching enabled compound/sequence rule contributes:

| Rule ID | Condition | Points | Floor |
|---|---|---:|---|
| `POL-NEW-LOCATION-ADMIN` | New location plus administrator-permission change | 20 | High |
| `POL-UNUSUAL-TIME-SECRET` | Unusual time plus secret access | 15 | None |
| `POL-NEW-SERVICE-BURST` | New service plus high frequency | 10 | None |
| `POL-PROTECTION-AFTER-PRIVILEGE` | Disable/remove protection after a privilege change in the correlated sequence | 30 | Critical |

### Functional Requirements

- **FR-001**: Events, profiles, baselines, policy results, AI context, and assessments MUST join through stable `identityId` and `eventId` values rather than display names.
- **FR-002**: The system MUST store normalized UTC security events with source, service, action, resource, outcome, correlation/session identifiers, and sufficient history for baseline and sequence rules.
- **FR-003**: The system MUST build versioned 30-day identity baselines containing usual hours/timezone, IPs/locations, services, actions, 15-minute frequency statistics, sample size, active-day count, confidence, and unknown fields.
- **FR-004**: A baseline MUST be low confidence below 20 valid events or 7 active days; dependent rules MUST report `unknown` and add zero when evidence is insufficient.
- **FR-005**: Policy rules MUST be stored/configured with rule ID, category, condition key, points, optional severity floor, enabled state, version, and human-readable explanation.
- **FR-006**: Rule conditions MUST be approved versioned condition keys implemented by the policy engine; arbitrary database expressions, Python, SQL, or user-provided executable rules are forbidden.
- **FR-007**: `policyScore` MUST equal `min(100, sum(all matched enabled context points) + highest matched enabled action points + highest matched enabled compound/sequence points)`.
- **FR-008**: The policy evaluation MUST retain matched, not-matched, unknown, and disabled results with evidence for every applicable rule in Policy Catalog v1.
- **FR-009**: The policy evaluation MUST calculate the strongest applicable severity floor independently of AI.
- **FR-010**: The AI prompt MUST receive only the normalized event, bounded correlated-event sequence, identity/baseline summary, policy results, and explicit rubric; raw fields MUST be clearly delimited as untrusted data.
- **FR-011**: The AI response MUST be validated structured data containing `adjustment`, `confidence`, `riskFactors`, `mitigatingFactors`, `evidenceEventIds`, and `explanation`, plus model/prompt version provenance recorded by the server.
- **FR-012**: The only valid AI adjustments are `-15`, `-5`, `0`, `10`, `20`, and `25`.
- **FR-013**: AI adjustment MUST be applied as zero when confidence is below 0.60, the response is malformed, evidence IDs are invalid, a positive adjustment has no evidence, a negative adjustment has no mitigation, or the AI service is unavailable.
- **FR-014**: The AI MUST NOT change policy matches, points, floors, policy score, severity thresholds, or final arithmetic directly.
- **FR-015**: `preFloorScore` MUST equal `clamp(policyScore + aiAdjustmentApplied, 0, 100)`.
- **FR-016**: `finalRiskScore` MUST equal `max(preFloorScore, severityFloorMinimum)`, where no floor is 0, High is 65, and Critical is 85.
- **FR-017**: Severity MUST be Low for 0–39, Medium for 40–64, High for 65–84, and Critical for 85–100.
- **FR-018**: Every assessment MUST persist its event, baseline version, full rule results, policy score/version, raw and applied AI decision/status/provenance, floor, final score, severity, and timestamps.
- **FR-019**: Equivalent assessment requests using identical event, baseline, policy snapshot, prompt version, model, and validated AI result MUST be idempotent.
- **FR-020**: Identity Profile responses MUST be database-derived and include profile metadata, recent events, latest baseline/confidence, matched policies, AI context status, and recent assessments while retaining existing UI card fields during migration.
- **FR-021**: Policy enable/disable operations MUST affect only future evaluations and MUST NOT mutate historical assessment results.
- **FR-022**: Dataset ingestion MUST be transactional for accepted batches, idempotent by `eventId`, and MUST reject or quarantine unresolved identities rather than attach them incorrectly.
- **FR-023**: The synthetic telemetry pack MUST separate identity directory data, normal historical events, evaluation events, mocked AI decisions, and expected assessment labels so expected answers never enter runtime prompts.
- **FR-024**: Synthetic telemetry MUST cover every Policy Catalog v1 rule, allowed AI adjustment, AI validation/failure path, severity floor/boundary, low-confidence baseline, duplicate, and unresolved identity case.
- **FR-025**: All sample data MUST be fictitious and contain no usable secret, token, credential, or real personal/production identifier.
- **FR-026**: REST contracts for richer ingestion, policies, identity profiles, assessment creation, and assessment retrieval MUST be defined before implementation resumes.

### Key Entities

- **Policy Rule**: Versioned deterministic rule with an approved condition key, points, optional severity floor, and enabled state.
- **Policy Evaluation**: Immutable per-assessment results for all applicable rules plus the capped policy base score and strongest floor.
- **AI Context Decision**: Validated bounded adjustment and explanation grounded in real evidence IDs, including raw/applied adjustment, status, confidence, prompt/model version, and validation outcome.
- **Risk Assessment**: Immutable combination of policy evaluation, applied AI adjustment, policy floor, final score, and severity.
- **Identity**: Stable human/service/workload principal owning events, baselines, and assessments.
- **Security Event**: Immutable normalized cloud/identity action linked to an identity and optionally correlated with a bounded sequence.
- **Identity Baseline**: Versioned snapshot of expected behavior with explicit confidence/unknown fields.
- **Synthetic Oracle**: Test-only expected rule/AI/final results stored separately from runtime inputs.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For 100% of policy fixtures, independent evaluation from the approved catalog produces identical rule results, policy score, floor, final score, and severity.
- **SC-002**: Invalid, low-confidence, unsupported, or unavailable AI output changes the policy-derived score by exactly zero in 100% of validation fixtures.
- **SC-003**: A policy severity floor is never bypassed by a negative AI adjustment in any test or runtime response.
- **SC-004**: Every nonzero applied AI adjustment cites at least one valid event ID; every negative adjustment also includes a specific mitigating factor.
- **SC-005**: After import, 100% of accepted events with valid identity IDs appear in the correct database-backed profile without restart or display-name guessing.
- **SC-006**: The synthetic oracle contains at least one independently testable case for every policy rule, allowed AI adjustment, failure path, floor, and severity boundary.
- **SC-007**: Re-importing duplicate event IDs creates zero duplicate event or equivalent assessment rows.
- **SC-008**: An analyst can trace any final score to the exact policy snapshot/results, AI decision/validation status, applied floor, evidence IDs, and versions from one assessment response.

## Assumptions

- Baselines retain the approved defaults: 30-day lookback, 15-minute frequency windows, historical p95, and 20 events across 7 active days for established confidence.
- Correlated AI/policy sequences are bounded to the same identity/session and at most 20 events within the preceding 60 minutes.
- The existing liteLLM-compatible proxy and 15-second timeout are reused.
- Policy-only scoring is always available; AI adjustment is an optional enhancement and defaults to zero on any uncertainty or failure.
- AI decisions are cached by event, baseline version, policy snapshot version, prompt version, and model.
- SQLite remains process-local for the hackathon; durable production persistence, auth, and multitenancy remain outside this feature.
- Existing API/UI fields remain available during migration; policy/AI details are additive.

## Out of Scope

- Isolation Forest or any other anomaly-model score in the risk calculation.
- Arbitrary user-authored executable policy expressions.
- AI-generated or AI-modified policy rules, points, floors, severity thresholds, or final arithmetic.
- Live cloud/provider integrations, automated remediation, durable database deployment, authentication, authorization, and multitenancy.
- Peer-group analytics or impossible-travel calculations unless later added as explicit policy condition keys.
