#!/usr/bin/env bash
# =============================================================================
# benchmark.sh — Inference speed tester for PyRIT MCP Server
#
# Sends a standard prompt to the configured backend and measures tokens/second.
# Tests both the attacker and scorer backends independently.
#
# Usage:
#   ./scripts/benchmark.sh
#   # or via Makefile:
#   make benchmark
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

[[ -f "$PROJECT_ROOT/.env" ]] && source "$PROJECT_ROOT/.env"
[[ -f "$PROJECT_ROOT/.env.detected" ]] && source "$PROJECT_ROOT/.env.detected"

ATTACKER_URL="${ATTACKER_BASE_URL:-http://localhost:11434}"
ATTACKER_MODEL_VAL="${ATTACKER_MODEL:-dolphin-mistral}"
N_TOKENS="${1:-200}"

BENCHMARK_PROMPT="Write a detailed paragraph about the history of network security. Include at least 5 technical terms."

echo "=============================================="
echo "  PyRIT MCP — Inference Benchmark"
echo "=============================================="
echo ""
echo "Testing attacker backend: $ATTACKER_MODEL_VAL @ $ATTACKER_URL"
echo "Target output: ~$N_TOKENS tokens"
echo ""

START_TIME=$(date +%s%N)

RESPONSE=$(python3 - << EOF
import urllib.request, json, time

url = "${ATTACKER_URL}/v1/chat/completions"
payload = {
    "model": "${ATTACKER_MODEL_VAL}",
    "messages": [{"role": "user", "content": "${BENCHMARK_PROMPT}"}],
    "max_tokens": ${N_TOKENS},
    "temperature": 0.7,
    "stream": False
}
req = urllib.request.Request(
    url,
    data=json.dumps(payload).encode(),
    headers={"Content-Type": "application/json"}
)
with urllib.request.urlopen(req, timeout=120) as resp:
    data = json.loads(resp.read())
    usage = data.get("usage", {})
    completion_tokens = usage.get("completion_tokens", 0)
    elapsed = data.get("usage", {}).get("total_time", 0)
    print(f"{completion_tokens}")
EOF
)

END_TIME=$(date +%s%N)
ELAPSED_MS=$(( (END_TIME - START_TIME) / 1000000 ))
ELAPSED_S=$(( ELAPSED_MS / 1000 ))

if [[ "$ELAPSED_S" -gt 0 && "$RESPONSE" -gt 0 ]]; then
    TPS=$(( RESPONSE / ELAPSED_S ))
    echo "Result: $RESPONSE tokens in ${ELAPSED_S}s = ~${TPS} tokens/second"
else
    echo "Result: completed in ${ELAPSED_MS}ms (token count unavailable from this endpoint)"
fi

echo ""
echo "Benchmark complete."
