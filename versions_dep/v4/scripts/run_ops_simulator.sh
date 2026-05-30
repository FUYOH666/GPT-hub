#!/usr/bin/env bash
# GPTHub v4 operational simulator wrapper.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ORCH_DIR="$ROOT/apps/orchestrator"
MODE="${1:-mock}"
shift || true

if [ -f "$ROOT/.env" ]; then
  set -a
  # shellcheck disable=SC1091
  source "$ROOT/.env"
  set +a
fi

export OPENROUTER_REFRESH_CATALOG_ON_STARTUP=false

cd "$ORCH_DIR"
REPORT="${OPS_REPORT:-$ROOT/reports/ops-${MODE}.json}"

exec uv run python -m gpthub_orchestrator.tools.ops_simulator \
  --mode="$MODE" \
  --report="$REPORT" \
  "$@"
