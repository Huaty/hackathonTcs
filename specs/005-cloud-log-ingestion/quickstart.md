# Quickstart: Cloud Log Ingestion and Replay

This guide describes the intended implementation verification. Commands that call ingestion endpoints will not pass until feature 005 tasks are implemented.

## 1. Regenerate and validate the synthetic pack

From the repository root:

```powershell
python datasets/cloud-ingestion/generate_raw_cloud_logs.py --output datasets/cloud-ingestion
python datasets/cloud-ingestion/generate_raw_cloud_logs.py --output datasets/cloud-ingestion --check
```

The second command must regenerate content in memory and verify the checked-in files and manifest digests without rewriting them.

## 2. Start the backend

```powershell
cd sentinel-access/backend
.venv/Scripts/python.exe -m uvicorn app.main:app --reload --port 8001
```

Use a disposable raw-store root during verification:

```powershell
$env:RAW_EVENT_STORE_PATH = "$PWD/.runtime/raw-events"
```

## 3. Load synthetic identity bindings

Feature 004 identities must already exist. Import/load `datasets/cloud-ingestion/identity-bindings.json` through the implementation-defined startup fixture path, then confirm binding counts match `manifest.json`.

## 4. Ingest AWS CloudTrail

```powershell
curl.exe -F "file=@../../datasets/cloud-ingestion/aws-cloudtrail.json" "http://localhost:8001/api/ingestion/batches?provider=aws_cloudtrail&sourceAccountId=111122223333"
```

Confirm the response includes `batchId`, `sha256`, counts, bounded errors, and `status=completed_with_errors` because the fixture includes controlled duplicate/quarantine cases.

## 5. Ingest Azure Activity Log

```powershell
curl.exe -F "file=@../../datasets/cloud-ingestion/azure-activity-log.json" "http://localhost:8001/api/ingestion/batches?provider=azure_activity_log&sourceAccountId=00000000-1111-2222-3333-444444444444"
```

## 6. Ingest GCP Audit Log

```powershell
curl.exe -F "file=@../../datasets/cloud-ingestion/gcp-audit-log.jsonl" "http://localhost:8001/api/ingestion/batches?provider=gcp_audit_log&sourceAccountId=sentinel-demo-001"
```

## 7. Verify batch lineage

```powershell
curl.exe "http://localhost:8001/api/ingestion/batches/<batchId>"
```

Confirm:

- Archived file digest matches the response.
- Every record has a stable raw-event ID and record index.
- Successful records link to a normalized event ID.
- Controlled failures have closed quarantine reason codes.

## 8. Verify idempotency

Repeat steps 4–6. Confirm the upload reports duplicate batches/records and creates no additional normalized event IDs.

## 9. Replay an archived batch

```powershell
curl.exe -X POST -H "Content-Type: application/json" -d '{"batchId":"<batchId>","targetNormalizerVersion":"cloud-normalizer-v1","mappingVersion":"identity-map-v1","reason":"Verify deterministic replay"}' "http://localhost:8001/api/ingestion/replays"
```

Retrieve the replay:

```powershell
curl.exe "http://localhost:8001/api/ingestion/replays/<replayId>"
```

Confirm the same-version replay is unchanged/idempotent, raw files are not modified, and no risk/LLM endpoint was invoked.

## 10. Compare normalized output with the oracle

Run the integration suite:

```powershell
cd sentinel-access/backend
.venv/Scripts/python.exe -m pytest tests/unit/test_raw_event_store.py tests/unit/test_cloud_normalizers.py tests/contract/test_ingestion_api.py tests/integration/test_cloud_ingestion_pipeline.py tests/integration/test_ingestion_replay.py
```

The pipeline test must compare every fixture record with `expected-normalized-events.jsonl` and verify manifest counts/digests.

## 11. Run regressions

```powershell
cd sentinel-access/backend
.venv/Scripts/python.exe -m pytest -q
```

```powershell
cd sentinel-access
npm run check
npm run build
```
