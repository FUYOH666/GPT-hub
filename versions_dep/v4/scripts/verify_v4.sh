#!/usr/bin/env bash
# Smoke check for GPTHub v4 stack (orchestrator only; Open WebUI optional).
set -euo pipefail

ORCH_URL="${ORCH_URL:-http://127.0.0.1:8089}"
KEY="${ORCHESTRATOR_API_KEY:-}"

if [ -z "$KEY" ]; then
  echo "Set ORCHESTRATOR_API_KEY" >&2
  exit 1
fi

curl -sf "$ORCH_URL/healthz" | grep -q '"status":"ok"'
curl -sf "$ORCH_URL/readyz" | grep -q '"status":"ready"'

TRACE=$(curl -sf "$ORCH_URL/v1/chat/completions" \
  -H "Authorization: Bearer $KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"gpt-hub","messages":[{"role":"user","content":"Say hi in one word."}]}' \
  -D - -o /tmp/gpthub_v4_smoke.json | grep -i X-GPTHub-Trace | tr -d '\r' | awk '{print $2}')

echo "Trace header present: ${TRACE:0:40}..."
python3 -c "import json; json.load(open('/tmp/gpthub_v4_smoke.json'))"
echo "v4 smoke OK"
