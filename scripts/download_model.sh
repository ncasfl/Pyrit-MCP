#!/usr/bin/env bash
# =============================================================================
# download_model.sh — GGUF model downloader for PyRIT MCP Server
#
# Downloads GGUF model files from HuggingFace to the local ./models/ directory.
# Checks available disk space and prompts for confirmation before downloading.
#
# Usage:
#   ./scripts/download_model.sh
#   # or via Makefile (interactive):
#   make download-model
#
# Environment variables:
#   HUGGINGFACE_TOKEN — required for gated models (set in .env)
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
MODELS_DIR="$PROJECT_ROOT/models"

[[ -f "$PROJECT_ROOT/.env" ]] && source "$PROJECT_ROOT/.env"
[[ -f "$PROJECT_ROOT/.env.detected" ]] && source "$PROJECT_ROOT/.env.detected"

# Load catalog
CATALOG="$PROJECT_ROOT/config/model_catalog.json"
if ! command -v python3 &>/dev/null; then
    echo "ERROR: python3 required for model catalog lookup"
    exit 1
fi

echo "=============================================="
echo "  PyRIT MCP — Model Downloader"
echo "=============================================="
echo ""
echo "Available models:"
python3 - "$CATALOG" << 'EOF'
import json, sys
catalog = json.load(open(sys.argv[1]))
for m in catalog["models"]:
    print(f"  {m['id']}")
    for q in m["quantizations"]:
        print(f"    {q['quant_id']:12s} ~{q['ram_gb']:.1f}GB  quality={q['quality_score']}/10  {q['gguf_filename']}")
EOF

echo ""
read -rp "Enter model ID (e.g. llama3.1-405b): " MODEL_ID
read -rp "Enter quantization (e.g. Q8_0): " QUANT_ID

# Look up model metadata
RESULT=$(python3 - "$CATALOG" "$MODEL_ID" "$QUANT_ID" << 'EOF'
import json, sys
catalog = json.load(open(sys.argv[1]))
model_id = sys.argv[2]
quant_id = sys.argv[3]
for m in catalog["models"]:
    if m["id"] == model_id:
        for q in m["quantizations"]:
            if q["quant_id"] == quant_id:
                print(f"{m['hf_repo']}|{q['gguf_filename']}|{q['ram_gb']}")
                sys.exit(0)
print("NOT_FOUND")
EOF
)

if [[ "$RESULT" == "NOT_FOUND" ]]; then
    echo "ERROR: Model '$MODEL_ID' with quantization '$QUANT_ID' not found in catalog."
    exit 1
fi

HF_REPO=$(echo "$RESULT" | cut -d'|' -f1)
FILENAME=$(echo "$RESULT" | cut -d'|' -f2)
RAM_GB=$(echo "$RESULT" | cut -d'|' -f3)

echo ""
echo "Model: $MODEL_ID ($QUANT_ID)"
echo "  HuggingFace repo: $HF_REPO"
echo "  File: $FILENAME"
echo "  RAM required: ~${RAM_GB}GB"
echo "  Download destination: $MODELS_DIR/$FILENAME"
echo ""

# Check available disk space
DISK_AVAILABLE_GB=$(df -BG "$MODELS_DIR" | tail -1 | awk '{print $4}' | tr -d 'G')
echo "Disk space available in models/: ~${DISK_AVAILABLE_GB}GB"

REQUIRED_GB=$(python3 -c "import math; print(math.ceil(float('$RAM_GB') * 1.1))")
if [[ "$DISK_AVAILABLE_GB" -lt "$REQUIRED_GB" ]]; then
    echo "WARNING: Insufficient disk space. Need ~${REQUIRED_GB}GB, have ${DISK_AVAILABLE_GB}GB."
    read -rp "Continue anyway? [y/N]: " FORCE
    [[ "${FORCE,,}" != "y" ]] && { echo "Aborted."; exit 0; }
fi

read -rp "Download $FILENAME (~${RAM_GB}GB)? [y/N]: " CONFIRM
[[ "${CONFIRM,,}" != "y" ]] && { echo "Aborted."; exit 0; }

echo ""
echo "Downloading via huggingface-cli..."

HF_ARGS=(
    "download"
    "$HF_REPO"
    "$FILENAME"
    "--local-dir" "$MODELS_DIR"
    "--local-dir-use-symlinks" "False"
)

if [[ -n "${HUGGINGFACE_TOKEN:-}" ]]; then
    HF_ARGS+=("--token" "$HUGGINGFACE_TOKEN")
fi

huggingface-cli "${HF_ARGS[@]}"

echo ""
echo "Download complete: $MODELS_DIR/$FILENAME"
echo ""
echo "To use this model, set in .env:"
echo "  LLAMACPP_MODEL_PATH=/models/$FILENAME"
echo "  ATTACKER_MODEL=$MODEL_ID"
echo "  ATTACKER_QUANTIZATION=$QUANT_ID"
