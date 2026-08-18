# Quickstart: Policy-First AI Contextual Risk Scoring

This describes intended verification after revised implementation. The existing partial Isolation Forest work is superseded and is not the expected contract.

## 1. Start services

```powershell
cd sentinel-access/backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8001
```

In another terminal:

```powershell
cd sentinel-access
pnpm dev
```

## 2. Verify Policy Catalog v1

```powershell
curl.exe http://localhost:8001/api/policies
```

Confirm every catalog rule exposes stable ID, approved condition key, points, optional floor, enabled state, and `policy-catalog-v1`; no executable expression is returned.

## 3. Import identity and baseline history

```powershell
curl.exe -F "file=@datasets/risk-scoring/identities.json" "http://localhost:8001/api/datasets?mode=identities"
curl.exe -F "file=@datasets/risk-scoring/baseline-events.jsonl" "http://localhost:8001/api/datasets?mode=events"
```

Confirm database-backed profiles show baseline sample count, active days, expected behavior, and confidence.

## 4. Import evaluation events

```powershell
curl.exe -F "file=@datasets/risk-scoring/evaluation-events.jsonl" "http://localhost:8001/api/datasets?mode=events"
```

Runtime events contain no expected score, AI answer, policy label, or scenario label.

## 5. Assess one event

```powershell
curl.exe -X POST -H "Content-Type: application/json" -d '{"eventId":"EVT-104","forceAiRefresh":false}' http://localhost:8001/api/risk-assessments
```

Verify manually:

```text
policyScore = context points + highest action points + highest compound/sequence points, capped 100
preFloorScore = clamp(policyScore + aiAdjustmentApplied, 0, 100)
finalRiskScore = max(preFloorScore, severityFloorMinimum)
```

## 6. Verify AI degradation

Run the assessment tests with the AI client mocked for timeout, malformed JSON, unsupported adjustment, confidence 0.59, nonexistent evidence ID, positive adjustment without evidence, negative adjustment without mitigation, and prompt-like event text. Each must apply adjustment zero and still return the policy assessment.

## 7. Verify floors

Test at least:

- `POL-DISABLE-PROTECTION` plus AI `-15`: final remains at least 65.
- `POL-PROTECTION-AFTER-PRIVILEGE` plus AI `-15`: final remains at least 85.
- No-floor policy score 20 plus AI `-15`: final may become 5.

## 8. Verify policy toggles and history

Disable `POL-NEW-SOURCE`, assess a matching event, and confirm the rule is `disabled` with zero award. Re-enable it and create a new assessment. Confirm the earlier assessment remains unchanged.

## 9. Verify Identity Profiles

Open the frontend profile for the assessed identity. Confirm it performs API requests and displays the stored baseline, policy score/matches, AI adjustment/status, floor, final score, and evidence—not local fixture text.

## 10. Run regression suites

```powershell
cd sentinel-access/backend
.\.venv\Scripts\python.exe -m pytest tests/unit tests/contract tests/integration

cd ..
pnpm check
pnpm build
```

Expected: no Isolation Forest request/storage/response field remains in Feature 004 tests or runtime API.
