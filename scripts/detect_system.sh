#!/usr/bin/env bash
# =============================================================================
# detect_system.sh — Hardware detection for PyRIT MCP Server
#
# Detects RAM, CPU topology, NUMA configuration, GPU availability, and
# system optimization settings. Writes results to .env.detected in the
# project root directory.
#
# Usage:
#   ./scripts/detect_system.sh
#   # or via Makefile:
#   make detect
#
# NOTE: This script is designed to run on the Linux machine where Docker
# will be deployed — NOT on Windows development machines. On Linux bare
# metal, Docker containers access all host RAM by default. On Docker
# Desktop (Mac/Windows), container memory is capped by the VM size.
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
OUTPUT_FILE="$PROJECT_ROOT/.env.detected"
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

echo "=============================================="
echo "  PyRIT MCP — System Hardware Detection"
echo "=============================================="
echo ""

# ── RAM Detection ─────────────────────────────────────────────────────────────
if [[ -f /proc/meminfo ]]; then
    TOTAL_RAM_KB=$(grep MemTotal /proc/meminfo | awk '{print $2}')
    AVAILABLE_RAM_KB=$(grep MemAvailable /proc/meminfo | awk '{print $2}')
    TOTAL_RAM_GB=$(( TOTAL_RAM_KB / 1024 / 1024 ))
    AVAILABLE_RAM_GB=$(( AVAILABLE_RAM_KB / 1024 / 1024 ))
else
    echo "WARNING: /proc/meminfo not found. Defaulting to 8GB detected RAM."
    TOTAL_RAM_GB=8
    AVAILABLE_RAM_GB=7
fi

echo "RAM: ${TOTAL_RAM_GB}GB total / ${AVAILABLE_RAM_GB}GB available"

# ── CPU Detection ─────────────────────────────────────────────────────────────
if command -v lscpu &>/dev/null; then
    CPU_CORES=$(lscpu | grep "^CPU(s):" | awk '{print $2}')
    CPU_SOCKETS=$(lscpu | grep "^Socket(s):" | awk '{print $2}')
    CPU_CORES_PER_SOCKET=$(lscpu | grep "^Core(s) per socket:" | awk '{print $4}')
    CPU_MODEL=$(lscpu | grep "^Model name:" | sed 's/Model name:\s*//')
else
    CPU_CORES=$(nproc)
    CPU_SOCKETS=1
    CPU_CORES_PER_SOCKET=$CPU_CORES
    CPU_MODEL="Unknown"
fi

echo "CPU: $CPU_MODEL"
echo "     $CPU_CORES logical cores / $CPU_SOCKETS socket(s)"

# ── NUMA Detection ────────────────────────────────────────────────────────────
NUMA_NODES=1
if command -v numactl &>/dev/null; then
    NUMA_NODES=$(numactl --hardware 2>/dev/null | grep "available:" | awk '{print $2}' || echo "1")
    echo "NUMA: $NUMA_NODES node(s) detected"
    if [[ "$NUMA_NODES" -gt 1 ]]; then
        echo "      Multi-socket system detected — NUMA optimization will be applied"
        echo "      Use --numa distribute in llama.cpp for 2-3x throughput on large models"
    fi
else
    echo "NUMA: numactl not available — assuming single NUMA node"
fi

# ── NVIDIA GPU Detection ──────────────────────────────────────────────────────
HAS_NVIDIA_GPU=false
GPU_VRAM_GB=0
NVIDIA_GPU_MODEL="none"
NVIDIA_DRIVER_VERSION="none"

if command -v nvidia-smi &>/dev/null; then
    if nvidia-smi &>/dev/null; then
        HAS_NVIDIA_GPU=true
        NVIDIA_GPU_MODEL=$(nvidia-smi --query-gpu=name --format=csv,noheader | head -1)
        NVIDIA_DRIVER_VERSION=$(nvidia-smi --query-gpu=driver_version --format=csv,noheader | head -1)
        GPU_VRAM_MB=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader | head -1 | awk '{print $1}')
        GPU_VRAM_GB=$(( GPU_VRAM_MB / 1024 ))
        echo "GPU:  NVIDIA $NVIDIA_GPU_MODEL (${GPU_VRAM_GB}GB VRAM, driver $NVIDIA_DRIVER_VERSION)"
    fi
else
    echo "GPU:  No NVIDIA GPU detected (nvidia-smi not found)"
fi

# ── AMD GPU Detection ─────────────────────────────────────────────────────────
HAS_AMD_GPU=false
AMD_GPU_MODEL="none"
AMD_GPU_VRAM_GB=0

if command -v rocm-smi &>/dev/null; then
    if rocm-smi &>/dev/null; then
        HAS_AMD_GPU=true
        AMD_GPU_MODEL=$(rocm-smi --showproductname 2>/dev/null | grep "GPU" | head -1 | sed 's/.*: //' || echo "AMD GPU")
        echo "GPU:  AMD ROCm GPU detected — $AMD_GPU_MODEL"
    fi
fi

# ── Docker GPU Support Detection ──────────────────────────────────────────────
NVIDIA_TOOLKIT_AVAILABLE=false
if command -v nvidia-container-toolkit &>/dev/null || [[ -f /usr/bin/nvidia-container-toolkit ]]; then
    NVIDIA_TOOLKIT_AVAILABLE=true
fi

NVIDIA_DOCKER_RUNTIME=false
if command -v docker &>/dev/null; then
    if docker info 2>/dev/null | grep -q "nvidia"; then
        NVIDIA_DOCKER_RUNTIME=true
    fi
fi

# ── Inference Mode Selection ───────────────────────────────────────────────────
INFERENCE_MODE=cpu
if [[ "$HAS_NVIDIA_GPU" == "true" && "$NVIDIA_DOCKER_RUNTIME" == "true" ]]; then
    INFERENCE_MODE=gpu-nvidia
elif [[ "$HAS_AMD_GPU" == "true" ]]; then
    INFERENCE_MODE=gpu-amd
fi
echo "Inference mode: $INFERENCE_MODE"

# ── Memory Lock Capability ────────────────────────────────────────────────────
MLOCK_LIMIT=$(ulimit -l 2>/dev/null || echo "unknown")
if [[ "$MLOCK_LIMIT" == "unlimited" ]]; then
    MLOCK_AVAILABLE=true
    echo "mlock: unlimited (optimal — model files can be locked in RAM)"
else
    MLOCK_AVAILABLE=false
    echo "mlock: limited to ${MLOCK_LIMIT}KB (WARNING: large models may be swapped)"
    echo "       Fix: add '* soft memlock unlimited' to /etc/security/limits.conf"
fi

# ── Transparent Huge Pages ────────────────────────────────────────────────────
THP_MODE="unknown"
if [[ -f /sys/kernel/mm/transparent_hugepage/enabled ]]; then
    THP_CONTENT=$(cat /sys/kernel/mm/transparent_hugepage/enabled)
    if echo "$THP_CONTENT" | grep -q "\[madvise\]"; then
        THP_MODE="madvise"
        echo "THP:  madvise (optimal)"
    elif echo "$THP_CONTENT" | grep -q "\[never\]"; then
        THP_MODE="never"
        echo "THP:  never (suboptimal — set to madvise for best performance)"
    elif echo "$THP_CONTENT" | grep -q "\[always\]"; then
        THP_MODE="always"
        echo "THP:  always (suboptimal — set to madvise for best performance)"
    fi
fi

# ── CPU Frequency Governor ────────────────────────────────────────────────────
CPU_GOVERNOR="unknown"
GOVERNOR_FILE="/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor"
if [[ -f "$GOVERNOR_FILE" ]]; then
    CPU_GOVERNOR=$(cat "$GOVERNOR_FILE")
    if [[ "$CPU_GOVERNOR" == "performance" ]]; then
        echo "Governor: $CPU_GOVERNOR (optimal)"
    else
        echo "Governor: $CPU_GOVERNOR (WARNING: use 'performance' for inference workloads)"
        echo "          Fix: echo performance | tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor"
    fi
fi

# ── Write .env.detected ──────────────────────────────────────────────────────
cat > "$OUTPUT_FILE" << EOF
# =============================================================================
# Auto-generated by: make detect (scripts/detect_system.sh)
# Timestamp: $TIMESTAMP
# DO NOT EDIT — re-run 'make detect' to refresh
# =============================================================================

# ── Hardware Detection ────────────────────────────────────────────────────────
DETECTED_TOTAL_RAM_GB=$TOTAL_RAM_GB
DETECTED_AVAILABLE_RAM_GB=$AVAILABLE_RAM_GB
DETECTED_CPU_CORES=$CPU_CORES
DETECTED_CPU_MODEL="$CPU_MODEL"
DETECTED_CPU_SOCKETS=$CPU_SOCKETS
DETECTED_NUMA_NODES=$NUMA_NODES
DETECTED_HAS_NVIDIA_GPU=$HAS_NVIDIA_GPU
DETECTED_HAS_AMD_GPU=$HAS_AMD_GPU
DETECTED_GPU_VRAM_GB=$GPU_VRAM_GB
DETECTED_NVIDIA_TOOLKIT=$NVIDIA_TOOLKIT_AVAILABLE
DETECTED_NVIDIA_DOCKER_RUNTIME=$NVIDIA_DOCKER_RUNTIME
DETECTED_INFERENCE_MODE=$INFERENCE_MODE
DETECTED_MLOCK_AVAILABLE=$MLOCK_AVAILABLE
DETECTED_THP_MODE=$THP_MODE
DETECTED_CPU_GOVERNOR=$CPU_GOVERNOR

# ── Recommendations (populated by: make recommend) ───────────────────────────
# Run 'make recommend' to populate these values based on detected hardware
RECOMMENDED_ATTACKER_BACKEND=
RECOMMENDED_ATTACKER_MODEL=
RECOMMENDED_ATTACKER_QUANTIZATION=
RECOMMENDED_ATTACKER_MODEL_FILE=
RECOMMENDED_ATTACKER_RAM_GB=
RECOMMENDED_ATTACKER_THREADS=
RECOMMENDED_ATTACKER_NUMA=
RECOMMENDED_SCORER_BACKEND=
RECOMMENDED_SCORER_MODEL=
RECOMMENDED_SCORER_QUANTIZATION=
RECOMMENDED_SCORER_RAM_GB=
RECOMMENDED_TOTAL_RAM_REQUIRED_GB=
RECOMMENDED_REMAINING_RAM_GB=
RECOMMENDED_COMPOSE_PROFILE=
RECOMMENDED_OLLAMA_NUM_THREADS=
RECOMMENDED_LLAMACPP_N_THREADS=
RECOMMENDED_LLAMACPP_NUMA=
RECOMMENDED_LLAMACPP_MLOCK=
RECOMMENDED_LLAMACPP_CTX_SIZE=
EOF

echo ""
echo "Wrote: $OUTPUT_FILE"
echo ""
echo "Next step: run 'make recommend' to generate model recommendations."
