#!/usr/bin/env bash
# =============================================================================
# validate_env.sh — Pre-flight environment check for PyRIT MCP Server
#
# Validates:
#   - Required environment variables are set
#   - mlock limit is sufficient for the configured models
#   - Transparent Huge Pages is set to madvise
#   - CPU governor is set to performance
#   - NUMA numactl is available on multi-socket systems
#
# Usage:
#   ./scripts/validate_env.sh
#   # or via Makefile:
#   make validate-env
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

ERRORS=0
WARNINGS=0

error() { echo "  [ERROR] $*"; (( ERRORS++ )); }
warn()  { echo "  [WARN]  $*"; (( WARNINGS++ )); }
ok()    { echo "  [OK]    $*"; }

echo "=============================================="
echo "  PyRIT MCP — Environment Validation"
echo "=============================================="
echo ""

# ── Load .env files if present ────────────────────────────────────────────────
[[ -f "$PROJECT_ROOT/.env.detected" ]] && source "$PROJECT_ROOT/.env.detected"
[[ -f "$PROJECT_ROOT/.env" ]] && source "$PROJECT_ROOT/.env"

# ── Required ENV var check ────────────────────────────────────────────────────
echo "Checking required environment variables..."
REQUIRED_VARS=(
    "ATTACKER_BACKEND"
    "ATTACKER_BASE_URL"
    "ATTACKER_MODEL"
    "SCORER_BACKEND"
)
for var in "${REQUIRED_VARS[@]}"; do
    if [[ -z "${!var:-}" ]]; then
        error "$var is not set. Copy .env.example to .env and configure it."
    else
        ok "$var = ${!var}"
    fi
done

# ── Scorer API key check ──────────────────────────────────────────────────────
SCORER_BACKEND_VAL="${SCORER_BACKEND:-}"
if [[ "$SCORER_BACKEND_VAL" == "openai" || "$SCORER_BACKEND_VAL" == "groq" ]]; then
    SCORER_KEY_ENV="${SCORER_API_KEY_ENV:-}"
    if [[ -z "$SCORER_KEY_ENV" ]]; then
        error "SCORER_API_KEY_ENV must be set when SCORER_BACKEND=$SCORER_BACKEND_VAL"
    elif [[ -z "${!SCORER_KEY_ENV:-}" ]]; then
        error "Environment variable '$SCORER_KEY_ENV' (referenced by SCORER_API_KEY_ENV) is empty or unset"
    else
        ok "Scorer API key env var '$SCORER_KEY_ENV' is set"
    fi
fi

# ── Linux-specific system checks ──────────────────────────────────────────────
if [[ "$(uname)" == "Linux" ]]; then
    echo ""
    echo "Checking Linux system optimizations..."

    # mlock
    MLOCK_LIMIT=$(ulimit -l 2>/dev/null || echo "unknown")
    REQUIRED_MLOCK_GB="${RECOMMENDED_ATTACKER_RAM_GB:-0}"
    if [[ "$MLOCK_LIMIT" == "unlimited" ]]; then
        ok "mlock: unlimited"
    elif [[ "$REQUIRED_MLOCK_GB" -gt 32 ]]; then
        error "mlock limit is '$MLOCK_LIMIT' KB but attacker model requires ~${REQUIRED_MLOCK_GB}GB."
        error "Add to /etc/security/limits.conf:  * soft memlock unlimited"
        error "                                    * hard memlock unlimited"
        error "Then log out and back in, or reboot."
    else
        warn "mlock limit is '$MLOCK_LIMIT' KB. Models under ~32GB may still work."
    fi

    # THP
    if [[ -f /sys/kernel/mm/transparent_hugepage/enabled ]]; then
        THP=$(cat /sys/kernel/mm/transparent_hugepage/enabled)
        if echo "$THP" | grep -q "\[madvise\]"; then
            ok "Transparent Huge Pages: madvise"
        else
            warn "Transparent Huge Pages is not 'madvise'. Run:"
            warn "  echo madvise > /sys/kernel/mm/transparent_hugepage/enabled"
            warn "For persistence, add to /etc/rc.local or a systemd unit."
        fi
    fi

    # CPU governor
    GOVERNOR_FILE="/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor"
    if [[ -f "$GOVERNOR_FILE" ]]; then
        GOVERNOR=$(cat "$GOVERNOR_FILE")
        if [[ "$GOVERNOR" == "performance" ]]; then
            ok "CPU governor: performance"
        else
            warn "CPU governor is '$GOVERNOR'. Use 'performance' for inference:"
            warn "  echo performance | tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor"
        fi
    fi

    # NUMA
    NUMA_NODES="${DETECTED_NUMA_NODES:-1}"
    if [[ "$NUMA_NODES" -gt 1 ]]; then
        if command -v numactl &>/dev/null; then
            ok "numactl available — NUMA topology is $NUMA_NODES nodes"
            if [[ -z "${LLAMACPP_NUMA:-}" || "${LLAMACPP_NUMA:-}" != "distribute" ]]; then
                warn "LLAMACPP_NUMA is not set to 'distribute'."
                warn "On dual-socket systems, set LLAMACPP_NUMA=distribute for 2-3x throughput."
            fi
        else
            warn "Multi-socket system detected but numactl is not installed."
            warn "Install it: apt-get install numactl"
        fi
    fi
fi

# ── Summary ───────────────────────────────────────────────────────────────────
echo ""
echo "=============================================="
if [[ "$ERRORS" -gt 0 ]]; then
    echo "Result: FAILED — $ERRORS error(s), $WARNINGS warning(s)"
    echo "        Fix errors before starting the server."
    exit 1
elif [[ "$WARNINGS" -gt 0 ]]; then
    echo "Result: PASSED with $WARNINGS warning(s)"
    echo "        Warnings are non-blocking but may affect performance."
else
    echo "Result: PASSED — all checks clean"
fi
echo "=============================================="
