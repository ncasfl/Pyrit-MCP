#!/usr/bin/env bash
# =============================================================================
# PyRIT MCP Server — Container Entrypoint
#
# Execution order:
#   1. Load .env file if present (for non-Docker environments)
#   2. Validate required environment variables — exit with clear error if any missing
#   3. Log active configuration summary (credentials redacted)
#   4. Initialise DuckDB database directory
#   5. Launch the FastMCP server over stdio
#
# This script must be kept fast: every millisecond here is felt by the user
# waiting for the MCP server to appear in Claude Desktop.
# =============================================================================

set -euo pipefail

# ---------------------------------------------------------------------------
# Colour output helpers (stderr only — stdout is reserved for MCP protocol)
# ---------------------------------------------------------------------------
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
RESET='\033[0m'

info()  { echo -e "${CYAN}[pyrit-mcp]${RESET} $*" >&2; }
warn()  { echo -e "${YELLOW}[pyrit-mcp WARN]${RESET} $*" >&2; }
ok()    { echo -e "${GREEN}[pyrit-mcp OK]${RESET} $*" >&2; }
fatal() { echo -e "${RED}[pyrit-mcp FATAL]${RESET} $*" >&2; exit 1; }

# ---------------------------------------------------------------------------
# Step 1: Load .env file if present (optional — env vars may come from
# docker run --env-file or docker compose environment: block instead)
# ---------------------------------------------------------------------------
if [ -f /app/.env ]; then
    info "Loading /app/.env"
    set -a
    # shellcheck disable=SC1091
    source /app/.env
    set +a
fi

# ---------------------------------------------------------------------------
# Step 2: Validate required environment variables
# ---------------------------------------------------------------------------
info "Validating configuration..."

ERRORS=0

# ATTACKER_BACKEND is always required
if [ -z "${ATTACKER_BACKEND:-}" ]; then
    warn "ATTACKER_BACKEND is not set (defaulting to 'ollama')"
    export ATTACKER_BACKEND="ollama"
fi

if [ -z "${ATTACKER_BASE_URL:-}" ]; then
    fatal "ATTACKER_BASE_URL is required but not set.
       Set it in your .env file:
         ATTACKER_BASE_URL=http://ollama:11434   (for Ollama)
         ATTACKER_BASE_URL=http://localhost:8080  (for llama.cpp)"
fi

if [ -z "${ATTACKER_MODEL:-}" ]; then
    fatal "ATTACKER_MODEL is required but not set.
       Set it in your .env file:
         ATTACKER_MODEL=dolphin-mistral   (for Ollama)
         ATTACKER_MODEL=llama3.1-405b     (for llama.cpp)"
fi

# If scorer is an LLM backend, validate its settings
SCORER_BACKEND="${SCORER_BACKEND:-substring}"
if [ "${SCORER_BACKEND}" != "substring" ] && [ "${SCORER_BACKEND}" != "classifier" ]; then
    if [ -z "${SCORER_BASE_URL:-}" ]; then
        warn "SCORER_BACKEND=${SCORER_BACKEND} but SCORER_BASE_URL is not set."
        ERRORS=$((ERRORS + 1))
    fi
    if [ -z "${SCORER_MODEL:-}" ]; then
        warn "SCORER_BACKEND=${SCORER_BACKEND} but SCORER_MODEL is not set."
        ERRORS=$((ERRORS + 1))
    fi
fi

if [ "${ERRORS}" -gt 0 ]; then
    fatal "${ERRORS} configuration error(s) detected. Check your .env file."
fi

ok "Configuration validated."

# ---------------------------------------------------------------------------
# Step 3: Log active configuration summary
# ---------------------------------------------------------------------------
DB_PATH="${PYRIT_DB_PATH:-/data/pyrit.db}"
SANDBOX="${PYRIT_SANDBOX_MODE:-false}"
LOG_LEVEL="${PYRIT_LOG_LEVEL:-INFO}"

info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
info " PyRIT MCP Server Configuration"
info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
info " Attacker backend : ${ATTACKER_BACKEND} / ${ATTACKER_MODEL}"
info " Attacker URL     : ${ATTACKER_BASE_URL}"
info " Scorer backend   : ${SCORER_BACKEND} / ${SCORER_MODEL:-n/a}"
info " Database path    : ${DB_PATH}"
info " Log level        : ${LOG_LEVEL}"
if [ "${SANDBOX}" = "true" ]; then
    warn " SANDBOX MODE ENABLED — No real requests will be sent to targets"
else
    info " Sandbox mode     : disabled (live mode)"
fi
info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# ---------------------------------------------------------------------------
# Step 4: Initialise database directory
# ---------------------------------------------------------------------------
DB_DIR="$(dirname "${DB_PATH}")"
if [ "${DB_PATH}" != ":memory:" ] && [ ! -d "${DB_DIR}" ]; then
    info "Creating database directory: ${DB_DIR}"
    mkdir -p "${DB_DIR}"
fi
ok "Database directory ready."

# ---------------------------------------------------------------------------
# Step 5: Launch the MCP server
# exec replaces this shell process so signals pass through cleanly to Python
# ---------------------------------------------------------------------------
info "Starting MCP server over stdio..."
exec python -m pyrit_mcp.server
