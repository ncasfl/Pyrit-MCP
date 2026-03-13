# pyrit-mcp

**MCP server wrapping Microsoft PyRIT for LLM-orchestrated AI red-teaming.**

[![CI](https://github.com/ncasfl/pyrit-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/ncasfl/pyrit-mcp/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![ghcr.io](https://img.shields.io/badge/container-ghcr.io%2Fncasfl%2Fpyrit--mcp-blue)](https://github.com/ncasfl/pyrit-mcp/pkgs/container/pyrit-mcp)

---

> ⚠️ **Responsible Use** — This tool is for **authorized security testing only**.
> You must have explicit written permission to test any target application.
> The project maintainers accept no liability for unauthorized or malicious use.
> Users are responsible for compliance with all applicable laws and regulations.

---

## Documentation

| Document | Description |
|----------|-------------|
| **[INSTALL.md](INSTALL.md)** | Step-by-step installation guide — Python setup, VS Code (Claude Code & GitHub Copilot), Claude Desktop, Docker |
| **[USER_GUIDE.md](USER_GUIDE.md)** | Comprehensive user guide — all 42 tools by domain, example prompts, workflows, and testing recommendations |
| **[ROADMAP.md](ROADMAP.md)** | Planned features, v0.2.0 development status, and PyRIT coverage gaps |
| [CHANGELOG.md](CHANGELOG.md) | Release history and change log |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Contribution guidelines |

---

## What This Is

An [MCP (Model Context Protocol)](https://modelcontextprotocol.io) server that exposes
[Microsoft PyRIT](https://github.com/Azure/PyRIT)'s AI red-teaming capabilities as
structured tools that Claude — or any MCP-compatible LLM — can orchestrate in real time.

**Without this server:** PyRIT runs static scripts and logs results to a database.

**With this server:** Claude acts as the test director. It chooses attack strategies,
interprets results, adapts mid-campaign, and writes structured vulnerability reports —
all through a clean tool interface.

### What you can do with it

- Run PyRIT's 1,400+ built-in adversarial prompts against any AI endpoint
- Execute multi-turn escalating attacks (Crescendo, PAIR, TAP, Skeleton Key)
- Score responses with LLM judges, keyword matchers, or local classifiers
- Chain prompt converters (Base64, ROT13, leetspeak, language translation, etc.)
- Generate structured vulnerability reports with Claude's reasoning
- Run everything fully offline with local LLMs — zero API cost, zero data leakage
- Try tools safely without real backends using **Sandbox Mode** (see [USER_GUIDE.md](USER_GUIDE.md#sandbox-mode))

---

## The Dual-LLM Architecture

PyRIT requires two LLM roles with opposing safety requirements:

| Role | Job | Safety Requirement |
|---|---|---|
| **Attacker LLM** | Generates adversarial prompts and jailbreaks | Must be **uncensored** — safety-filtered models refuse this job |
| **Scorer LLM** | Judges whether a target response contains harmful content | Can be safety-filtered — it evaluates, not generates |

These two backends are **independently configurable**. You can run an uncensored local
model as the attacker while using GPT-4o as the scorer, or run both locally for full
offline operation.

---

## Quick Start

> **New here?** See [INSTALL.md](INSTALL.md) for detailed setup instructions covering
> Python environments, VS Code extensions (Claude Code & GitHub Copilot), Claude Desktop,
> and Docker — with platform-specific guidance for Windows, macOS, and Linux.

### Prerequisites

- Docker and Docker Compose
- [Claude Desktop](https://claude.ai/download) or Claude Code
- 8GB+ RAM (see [Tier Selection Guide](#tier-selection-guide) for model recommendations)

### 1. Clone and configure

```bash
git clone https://github.com/ncasfl/pyrit-mcp.git
cd pyrit-mcp
cp .env.example .env
# Edit .env with your attacker and scorer backend settings
```

### 2. Build the images

```bash
make build
```

### 3. Start the stack

```bash
# CPU only, Ollama attacker (default — works on any machine)
make up

# With NVIDIA GPU acceleration
make up-gpu

# High-RAM Tier 5/6/7 (llama.cpp + Ollama)
make up-llamacpp
```

### 4. Configure Claude Desktop

Add to your Claude Desktop `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "pyrit": {
      "command": "docker",
      "args": [
        "run", "--rm", "-i",
        "--env-file", "/absolute/path/to/pyrit-mcp/.env",
        "-v", "pyrit-db:/data",
        "-v", "/absolute/path/to/pyrit-mcp/datasets:/datasets",
        "ghcr.io/ncasfl/pyrit-mcp:latest"
      ]
    }
  }
}
```

> **Important flags:**
> - `--rm` — removes the container after the session ends
> - `-i` — keeps stdin open for MCP stdio transport (required)
> - `--env-file` — injects secrets without embedding them in the command
> - Do NOT add `-t` — this breaks the MCP stdio protocol

### 5. Start a red-team session in Claude

Claude will have access to all PyRIT tools. Try:

> "Configure an OpenAI-compatible target at http://localhost:8000, load the jailbreak-classic
> dataset, run a prompt sending attack with 10 samples, and show me the results."

---

## Tier Selection Guide

> **Linux bare-metal note:** On Linux, Docker containers access all available system RAM
> by default. No memory limit flags are needed. Docker Desktop on Mac/Windows caps
> container memory to the VM size — configure this in Docker Desktop settings.

### Tier 1 — 8-16 GB RAM

```bash
ATTACKER_BACKEND=ollama
ATTACKER_MODEL=dolphin-mistral       # ~4GB RAM
SCORER_BACKEND=substring             # no LLM scorer needed
```

Best for: Basic prompt injection and dataset attack testing. Crescendo not viable.

---

### Tier 2 — 17-31 GB RAM

```bash
ATTACKER_BACKEND=ollama
ATTACKER_MODEL=dolphin-mixtral:8x7b  # ~26GB RAM
SCORER_BACKEND=classifier            # toxic-bert local classifier
```

Best for: Most single-turn orchestrators. Basic Crescendo with quality tradeoffs.

---

### Tier 3 — 32-63 GB RAM

```bash
ATTACKER_BACKEND=ollama
ATTACKER_MODEL=dolphin-mixtral:8x22b  # ~48GB RAM
SCORER_BACKEND=ollama
SCORER_MODEL=nous-hermes2             # ~7GB RAM (separate Ollama instance)
COMPOSE_PROFILE=dual-ollama
```

Best for: Full orchestrator suite including Crescendo and PAIR.

---

### Tier 4 — 64-127 GB RAM

```bash
ATTACKER_BACKEND=ollama
ATTACKER_MODEL=dolphin-mixtral:8x22b  # Q6_K ~58GB, or llama3.1:405b Q2_K at 100GB+
SCORER_BACKEND=ollama
SCORER_MODEL=llama3.1:70b             # Q4_K_M ~40GB
COMPOSE_PROFILE=dual-ollama
```

Best for: High-quality multi-turn attacks. Tree-of-Attacks viable. Most professional engagements.

---

### Tier 5 — 128-255 GB RAM

```bash
ATTACKER_BACKEND=llamacpp
LLAMACPP_MODEL_PATH=/models/Meta-Llama-3.1-405B-Instruct-Q4_K_M.gguf  # ~220GB
SCORER_BACKEND=ollama
SCORER_MODEL=llama3.1:70b  # Q8_0 ~70GB
COMPOSE_PROFILE=full-llamacpp
```

Best for: Near-frontier attack quality. High-value AI application testing.

---

### Tier 6 — 256-511 GB RAM

```bash
ATTACKER_BACKEND=llamacpp
LLAMACPP_MODEL_PATH=/models/Meta-Llama-3.1-405B-Instruct-Q5_K_M.gguf  # ~265GB
LLAMACPP_NUMA=distribute   # critical for dual-socket systems
SCORER_BACKEND=ollama
SCORER_MODEL=llama3.1:70b  # Q8_0 ~70GB
```

Best for: Frontier-adjacent attack quality with zero content filtering.

---

### Tier 7 — 512 GB+ RAM

```bash
ATTACKER_BACKEND=llamacpp
LLAMACPP_MODEL_PATH=/models/Meta-Llama-3.1-405B-Instruct-Q8_0.gguf  # ~400GB
LLAMACPP_NUMA=distribute   # mandatory on dual-socket
LLAMACPP_MLOCK=true        # requires unlimited mlock
SCORER_BACKEND=ollama
SCORER_MODEL=llama3.1:70b  # FP16 ~140GB
```

Best for: Professional AI security research. 405B Q8_0 at full quality exceeds most
commercial red-team platforms, with no content filtering and zero data leakage.

Run `make detect && make recommend` on your Linux deployment machine to auto-generate
the optimal configuration for your hardware.

---

## Linux Bare Metal Optimizations

These settings significantly improve inference throughput on large models.

### NUMA (critical for dual-socket systems)

On any dual-socket system (EPYC, Threadripper, Xeon), `--numa distribute` is mandatory.
Without it, llama.cpp incurs cross-socket memory bus penalties that can cut throughput
by 2-3x on models too large to fit in a single NUMA node's memory.

```bash
LLAMACPP_NUMA=distribute
```

Detection: `make detect` reads `numactl --hardware` and sets this automatically.

### Memory Lock

Prevents large model files from being swapped to disk mid-inference.

```bash
# /etc/security/limits.conf
* soft memlock unlimited
* hard memlock unlimited
```

Then log out and back in (or reboot). Check: `ulimit -l` should show `unlimited`.

### Transparent Huge Pages

```bash
echo madvise > /sys/kernel/mm/transparent_hugepage/enabled
# Persistent: add to /etc/rc.local
```

### CPU Frequency Governor

```bash
echo performance | tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor
```

Run `make validate-env` on the Linux deployment machine to check all of these.

---

## Downloading GGUF Models

```bash
# Interactive downloader — prompts for model and quantization
make download-model

# Requires for gated models (Meta-Llama, etc.):
# Set HUGGINGFACE_TOKEN= in .env
```

Models are downloaded to `./models/` and bind-mounted read-only into the container.
They persist across container rebuilds and `docker compose down` cycles.

---

## Available Tools

> For detailed documentation on every tool — parameters, example Claude prompts, tips,
> and end-to-end workflows — see the **[User Guide](USER_GUIDE.md)**.

### Domain 1 — Target Management
`pyrit_configure_http_target` · `pyrit_configure_openai_target` · `pyrit_configure_azure_target`
`pyrit_list_targets` · `pyrit_remove_target` · `pyrit_test_target_connectivity`

### Domain 2 — Attack Orchestration
`pyrit_run_prompt_sending_orchestrator` · `pyrit_run_crescendo_orchestrator`
`pyrit_run_pair_orchestrator` · `pyrit_run_tree_of_attacks_orchestrator`
`pyrit_run_skeleton_key_orchestrator` · `pyrit_run_flip_orchestrator`
`pyrit_cancel_attack` · `pyrit_get_attack_status`

### Domain 3 — Datasets & Prompt Libraries
`pyrit_list_builtin_datasets` · `pyrit_load_dataset` · `pyrit_preview_dataset`
`pyrit_create_custom_dataset` · `pyrit_import_dataset_from_file`
`pyrit_list_session_datasets` · `pyrit_merge_datasets`

### Domain 4 — Scorers
`pyrit_configure_llm_scorer` · `pyrit_configure_substring_scorer`
`pyrit_configure_classifier_scorer` · `pyrit_score_response`
`pyrit_score_attack_results` · `pyrit_list_scorers` · `pyrit_get_score_distribution`

### Domain 5 — Results & Reporting
`pyrit_list_attacks` · `pyrit_get_attack_results` · `pyrit_get_successful_jailbreaks`
`pyrit_get_failed_attacks` · `pyrit_export_results_csv`
`pyrit_generate_report` · `pyrit_compare_attacks` · `pyrit_clear_session`

### Domain 6 — Converters
`pyrit_list_converters` · `pyrit_apply_converter` · `pyrit_chain_converters`

### Domain 7 — Backend Management
`pyrit_configure_attacker_backend` · `pyrit_configure_scorer_backend`
`pyrit_list_backend_options` · `pyrit_test_backend_connectivity`
`pyrit_estimate_attack_cost` · `pyrit_recommend_models`
`pyrit_pull_ollama_model` · `pyrit_list_ollama_models` · `pyrit_benchmark_backend`

---

## Docker Compose Profiles

| Profile | Services | Use Case |
|---|---|---|
| *(none)* | pyrit-mcp only | External/cloud LLM backends |
| `local-llm` | + Ollama (CPU) | CPU-only local inference |
| `local-llm-gpu` | + Ollama (NVIDIA) | GPU-accelerated |
| `local-llm-amd` | + Ollama (ROCm) | AMD GPU |
| `local-scorer` | + classifier sidecar | Local HuggingFace scorer |
| `dual-ollama` | + two Ollama instances | Independent attacker + scorer (Tier 3+) |
| `full` | all CPU services | Fully offline CPU stack |
| `full-llamacpp` | + llama.cpp + Ollama scorer | Tier 5/6/7 high-RAM |

---

## Development

```bash
make install    # Install deps + pre-commit hooks
make test       # Run unit tests
make lint       # Lint and format check
make typecheck  # mypy
make up-dev     # Hot-reload dev mode
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for full contribution guidelines.

---

## License

[MIT](LICENSE) — Copyright (c) 2026 Christopher Hohman
