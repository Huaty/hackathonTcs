# Quickstart: AI-Assisted Investigation Features

Validates the feature end-to-end once implemented. Assumes the 001
FastAPI backend migration is already running per its own `quickstart.md`
(backend on `:8001`, frontend dev server proxying `/api/*`).

## Prerequisites

1. A liteLLM proxy reachable at the URL you'll set as `LITELLM_PROXY_URL`
   (default `http://localhost:4000`), configured with a model alias matching
   `LITELLM_MODEL` (default `genailab-maas-Opus-4.6`) routed to Claude Opus
   4.6, and a virtual key for `LITELLM_API_KEY`.
2. Confirm the proxy works standalone before wiring the backend to it:
   ```bash
   curl -X POST http://localhost:4000/v1/chat/completions \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer $LITELLM_API_KEY" \
     -d '{"model": "genailab-maas-Opus-4.6", "messages": [{"role": "user", "content": "Hello!"}]}'
   ```
   Expect a `chat.completion` response with a non-empty `choices[0].message.content`.
3. Export the three env vars for the backend process:
   ```bash
   export LITELLM_PROXY_URL=http://localhost:4000
   export LITELLM_API_KEY=sk-...
   export LITELLM_MODEL=genailab-maas-Opus-4.6
   ```

## Step 1 — Start the backend

```bash
cd sentinel-access/backend
uvicorn app.main:app --reload --port 8001
```

## Step 2 — Finding explanation (FR-001/FR-002, SC-001/SC-002)

```bash
curl -s http://localhost:8001/api/findings/ALT-2841/explanation | jq
# expect: {"findingId": "ALT-2841", "explanation": "<specific to this finding>", "source": "ai"}

# Second call — should be near-instant (cached), same explanation text:
curl -s http://localhost:8001/api/findings/ALT-2841/explanation | jq
```

Pick a second, different finding ID from `GET /api/command-center` and
confirm its explanation text differs from the first (proves it's generated
from that finding's own evidence, not a shared template — SC-001).

## Step 3 — Ask Sentinel copilot (FR-003/FR-004/FR-005, SC-003)

```bash
curl -s -X POST http://localhost:8001/api/copilot/query \
  -H "Content-Type: application/json" \
  -d '{"question": "show me high-risk findings on AWS IAM"}' | jq
# expect: "answer" plus a non-empty "findings" array whose entries actually
# have service "AWS IAM" and a high score

curl -s -X POST http://localhost:8001/api/copilot/query \
  -H "Content-Type: application/json" \
  -d '{"question": "what is the capital of France"}' | jq
# expect: a graceful decline in "answer"; all three list fields empty
```

## Step 4 — AI report narrative (FR-006, SC-005)

Requires 001's `POST /api/reports/{title}/prepare` to be implemented.

```bash
curl -s -X POST "http://localhost:8001/api/reports/Today's%20security%20summary/prepare" | jq
# expect: existing "status"/"preparedAt" fields plus a non-null "narrative"

# Simulate a new anomaly, then prepare the same report again:
curl -s -X POST http://localhost:8001/api/findings/simulate-anomaly > /dev/null
curl -s -X POST "http://localhost:8001/api/reports/Today's%20security%20summary/prepare" | jq -r .narrative
# expect: narrative text differs from Step 4's first call (reflects the new finding)
```

## Step 5 — Fallback behavior (FR-007, SC-004)

Stop the liteLLM proxy (or point `LITELLM_PROXY_URL` at an unreachable
address) and re-run Steps 2-4:

- Explanation endpoint still returns 200 with `"source": "fallback"` and the
  finding's existing description/baseline text.
- Copilot still returns 200 with an "AI assistant is unavailable" answer and
  empty result arrays — not a 5xx.
- Report prepare still returns 200 with `"status": "ready"` and
  `"narrative": null` — the non-AI confirmation is unaffected.

Restart the proxy and re-run Step 2 for the same finding ID — confirm the
cached explanation from before the outage is still served unchanged.
