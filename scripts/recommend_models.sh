#!/usr/bin/env bash
# =============================================================================
# recommend_models.sh — Model recommendation engine for PyRIT MCP Server
#
# Reads .env.detected (written by detect_system.sh) and config/tier_profiles.json
# to produce ranked model recommendations. Appends recommendations back to
# .env.detected.
#
# Usage:
#   ./scripts/recommend_models.sh
#   # or via Makefile:
#   make recommend
#
# Prerequisites: detect_system.sh must have been run first (make detect)
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
ENV_DETECTED="$PROJECT_ROOT/.env.detected"

if [[ ! -f "$ENV_DETECTED" ]]; then
    echo "ERROR: .env.detected not found. Run 'make detect' first."
    exit 1
fi

# Load detected values
source "$ENV_DETECTED"

RAM_GB="${DETECTED_AVAILABLE_RAM_GB:-8}"
INFERENCE_MODE="${DETECTED_INFERENCE_MODE:-cpu}"
GPU_VRAM_GB="${DETECTED_GPU_VRAM_GB:-0}"
NUMA_NODES="${DETECTED_NUMA_NODES:-1}"
CPU_CORES="${DETECTED_CPU_CORES:-4}"
MLOCK_AVAILABLE="${DETECTED_MLOCK_AVAILABLE:-false}"

echo "=============================================="
echo "  PyRIT MCP — Model Recommendation Engine"
echo "=============================================="
echo ""
echo "Available RAM: ${RAM_GB}GB"
echo "Inference mode: $INFERENCE_MODE"
echo ""

# ── NUMA flag ────────────────────────────────────────────────────────────────
NUMA_FLAG=""
if [[ "${NUMA_NODES:-1}" -gt 1 ]]; then
    NUMA_FLAG="distribute"
fi

# ── Recommendation logic ──────────────────────────────────────────────────────
ATTACKER_BACKEND=""
ATTACKER_MODEL=""
ATTACKER_QUANT=""
ATTACKER_MODEL_FILE=""
ATTACKER_RAM_GB=0
ATTACKER_THREADS=4
SCORER_BACKEND=""
SCORER_MODEL=""
SCORER_QUANT=""
SCORER_RAM_GB=0
COMPOSE_PROFILE=""
LLAMACPP_CTX_SIZE=4096
LLAMACPP_MLOCK="false"

if [[ "$RAM_GB" -lt 12 ]]; then
    # ── Tier 1: < 12 GB ──────────────────────────────────────────────────────
    echo "Tier: 1 (< 12 GB RAM)"
    ATTACKER_BACKEND="ollama"
    ATTACKER_MODEL="dolphin-mistral"
    ATTACKER_QUANT="Q4_K_M"
    ATTACKER_MODEL_FILE="dolphin-2.1-mistral-7b.Q4_K_M.gguf"
    ATTACKER_RAM_GB=5
    ATTACKER_THREADS=4
    SCORER_BACKEND="substring"
    SCORER_MODEL="substring"
    SCORER_QUANT=""
    SCORER_RAM_GB=0
    COMPOSE_PROFILE="local-llm"
    LLAMACPP_CTX_SIZE=2048

elif [[ "$RAM_GB" -lt 32 ]]; then
    # ── Tier 2: 12-31 GB ─────────────────────────────────────────────────────
    echo "Tier: 2 (12-31 GB RAM)"
    ATTACKER_BACKEND="ollama"
    ATTACKER_MODEL="dolphin-mixtral:8x7b"
    ATTACKER_QUANT="Q4_K_M"
    ATTACKER_MODEL_FILE="dolphin-2.7-mixtral-8x7b.Q4_K_M.gguf"
    ATTACKER_RAM_GB=26
    ATTACKER_THREADS=8
    SCORER_BACKEND="classifier"
    SCORER_MODEL="unitary/toxic-bert"
    SCORER_QUANT=""
    SCORER_RAM_GB=1
    COMPOSE_PROFILE="local-llm"
    LLAMACPP_CTX_SIZE=4096

elif [[ "$RAM_GB" -lt 64 ]]; then
    # ── Tier 3: 32-63 GB ─────────────────────────────────────────────────────
    echo "Tier: 3 (32-63 GB RAM)"
    ATTACKER_BACKEND="ollama"
    ATTACKER_MODEL="dolphin-mixtral:8x22b"
    ATTACKER_QUANT="Q4_K_M"
    ATTACKER_MODEL_FILE="dolphin-2.9-mixtral-8x22b.Q4_K_M.gguf"
    ATTACKER_RAM_GB=48
    ATTACKER_THREADS=16
    SCORER_BACKEND="ollama"
    SCORER_MODEL="nous-hermes2"
    SCORER_QUANT="Q4_K_M"
    SCORER_RAM_GB=7
    COMPOSE_PROFILE="dual-ollama"
    LLAMACPP_CTX_SIZE=8192

elif [[ "$RAM_GB" -lt 128 ]]; then
    # ── Tier 4: 64-127 GB ────────────────────────────────────────────────────
    echo "Tier: 4 (64-127 GB RAM)"
    if [[ "$RAM_GB" -ge 100 ]]; then
        echo "NOTE: RAM >= 100GB — recommending llama3.1:405b Q2_K (low quality, max fit)"
        echo "      Consider dolphin-mixtral:8x22b Q6_K for better attack quality"
        ATTACKER_MODEL="llama3.1:405b"
        ATTACKER_QUANT="Q2_K"
        ATTACKER_MODEL_FILE="Meta-Llama-3.1-405B-Instruct-Q2_K.gguf"
        ATTACKER_RAM_GB=100
    else
        ATTACKER_MODEL="dolphin-mixtral:8x22b"
        ATTACKER_QUANT="Q6_K"
        ATTACKER_MODEL_FILE="dolphin-2.9-mixtral-8x22b.Q6_K.gguf"
        ATTACKER_RAM_GB=58
    fi
    ATTACKER_BACKEND="ollama"
    ATTACKER_THREADS=32
    SCORER_BACKEND="ollama"
    SCORER_MODEL="llama3.1:70b"
    SCORER_QUANT="Q4_K_M"
    SCORER_RAM_GB=40
    COMPOSE_PROFILE="dual-ollama"
    LLAMACPP_CTX_SIZE=16384

elif [[ "$RAM_GB" -lt 256 ]]; then
    # ── Tier 5: 128-255 GB ───────────────────────────────────────────────────
    echo "Tier: 5 (128-255 GB RAM)"
    ATTACKER_BACKEND="llamacpp"
    ATTACKER_MODEL="llama3.1:405b"
    ATTACKER_QUANT="Q4_K_M"
    ATTACKER_MODEL_FILE="Meta-Llama-3.1-405B-Instruct-Q4_K_M.gguf"
    ATTACKER_RAM_GB=220
    ATTACKER_THREADS=$(( CPU_CORES / 2 ))
    SCORER_BACKEND="ollama"
    SCORER_MODEL="llama3.1:70b"
    SCORER_QUANT="Q8_0"
    SCORER_RAM_GB=70
    COMPOSE_PROFILE="full-llamacpp"
    LLAMACPP_CTX_SIZE=32768
    LLAMACPP_MLOCK="true"

elif [[ "$RAM_GB" -lt 512 ]]; then
    # ── Tier 6: 256-511 GB ───────────────────────────────────────────────────
    echo "Tier: 6 (256-511 GB RAM)"
    ATTACKER_BACKEND="llamacpp"
    ATTACKER_MODEL="llama3.1:405b"
    ATTACKER_QUANT="Q5_K_M"
    ATTACKER_MODEL_FILE="Meta-Llama-3.1-405B-Instruct-Q5_K_M.gguf"
    ATTACKER_RAM_GB=265
    ATTACKER_THREADS=$(( CPU_CORES / 2 ))
    SCORER_BACKEND="ollama"
    SCORER_MODEL="llama3.1:70b"
    SCORER_QUANT="Q8_0"
    SCORER_RAM_GB=70
    COMPOSE_PROFILE="full-llamacpp"
    LLAMACPP_CTX_SIZE=32768
    LLAMACPP_MLOCK="true"

else
    # ── Tier 7: 512+ GB ──────────────────────────────────────────────────────
    echo "Tier: 7 (512+ GB RAM — Professional AI Security Research Grade)"
    ATTACKER_BACKEND="llamacpp"
    ATTACKER_MODEL="llama3.1:405b"
    ATTACKER_QUANT="Q8_0"
    ATTACKER_MODEL_FILE="Meta-Llama-3.1-405B-Instruct-Q8_0.gguf"
    ATTACKER_RAM_GB=400
    ATTACKER_THREADS=$(( CPU_CORES / 2 ))
    SCORER_BACKEND="ollama"
    SCORER_MODEL="llama3.1:70b"
    SCORER_QUANT="FP16"
    SCORER_RAM_GB=140
    COMPOSE_PROFILE="full-llamacpp"
    LLAMACPP_CTX_SIZE=32768
    LLAMACPP_MLOCK="true"

    REMAINING_RAM=$(( RAM_GB - ATTACKER_RAM_GB - SCORER_RAM_GB ))
    echo ""
    echo "Tier 7 headroom: ~${REMAINING_RAM}GB remaining after attacker + scorer"
    echo "               This can host a third specialized model for domain-specific attacks."
fi

# ── GPU layer override ────────────────────────────────────────────────────────
LLAMACPP_N_GPU_LAYERS=0
OLLAMA_GPU_LAYERS=0
if [[ "$INFERENCE_MODE" == "gpu-nvidia" && "$GPU_VRAM_GB" -gt 0 ]]; then
    echo ""
    echo "GPU detected (${GPU_VRAM_GB}GB VRAM) — GPU layer offloading will be applied"
    LLAMACPP_N_GPU_LAYERS=-1
    OLLAMA_GPU_LAYERS=-1
fi

TOTAL_RAM_REQUIRED=$(( ATTACKER_RAM_GB + SCORER_RAM_GB ))
REMAINING_RAM=$(( RAM_GB - TOTAL_RAM_REQUIRED ))
RECOMMENDED_THREADS=$(( CPU_CORES / 2 ))

# ── Append recommendations to .env.detected ──────────────────────────────────
# Use sed/awk to replace placeholder lines already in the file
update_env() {
    local key="$1"
    local value="$2"
    if grep -q "^${key}=" "$ENV_DETECTED"; then
        sed -i "s|^${key}=.*|${key}=${value}|" "$ENV_DETECTED"
    else
        echo "${key}=${value}" >> "$ENV_DETECTED"
    fi
}

update_env "RECOMMENDED_ATTACKER_BACKEND" "$ATTACKER_BACKEND"
update_env "RECOMMENDED_ATTACKER_MODEL" "$ATTACKER_MODEL"
update_env "RECOMMENDED_ATTACKER_QUANTIZATION" "$ATTACKER_QUANT"
update_env "RECOMMENDED_ATTACKER_MODEL_FILE" "$ATTACKER_MODEL_FILE"
update_env "RECOMMENDED_ATTACKER_RAM_GB" "$ATTACKER_RAM_GB"
update_env "RECOMMENDED_ATTACKER_THREADS" "$ATTACKER_THREADS"
update_env "RECOMMENDED_ATTACKER_NUMA" "$NUMA_FLAG"
update_env "RECOMMENDED_SCORER_BACKEND" "$SCORER_BACKEND"
update_env "RECOMMENDED_SCORER_MODEL" "$SCORER_MODEL"
update_env "RECOMMENDED_SCORER_QUANTIZATION" "$SCORER_QUANT"
update_env "RECOMMENDED_SCORER_RAM_GB" "$SCORER_RAM_GB"
update_env "RECOMMENDED_TOTAL_RAM_REQUIRED_GB" "$TOTAL_RAM_REQUIRED"
update_env "RECOMMENDED_REMAINING_RAM_GB" "$REMAINING_RAM"
update_env "RECOMMENDED_COMPOSE_PROFILE" "$COMPOSE_PROFILE"
update_env "RECOMMENDED_OLLAMA_NUM_THREADS" "$RECOMMENDED_THREADS"
update_env "RECOMMENDED_LLAMACPP_N_THREADS" "$ATTACKER_THREADS"
update_env "RECOMMENDED_LLAMACPP_NUMA" "$NUMA_FLAG"
update_env "RECOMMENDED_LLAMACPP_MLOCK" "$LLAMACPP_MLOCK"
update_env "RECOMMENDED_LLAMACPP_CTX_SIZE" "$LLAMACPP_CTX_SIZE"

echo ""
echo "Recommendations:"
echo "  Attacker: $ATTACKER_MODEL ($ATTACKER_QUANT) via $ATTACKER_BACKEND — ~${ATTACKER_RAM_GB}GB RAM"
echo "  Scorer:   $SCORER_MODEL${SCORER_QUANT:+ ($SCORER_QUANT)} via $SCORER_BACKEND — ~${SCORER_RAM_GB}GB RAM"
echo "  Profile:  $COMPOSE_PROFILE"
echo "  Total RAM: ~${TOTAL_RAM_REQUIRED}GB required / ${RAM_GB}GB available"
echo ""
echo "Written to: $ENV_DETECTED"
echo ""
echo "Next steps:"
echo "  1. Run 'make validate-env' to check system optimizations"
echo "  2. Copy .env.example to .env and fill in your settings"
echo "  3. Run 'make build' to build Docker images"
echo "  4. Run 'make up' to start with recommended profile"
