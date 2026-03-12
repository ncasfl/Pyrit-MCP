# PyRIT MCP Server — Comprehensive Project Plan
## Complete Reference Document for Claude Sonnet 4.6 Project Execution


**Status:** Phase 1 Complete — Phase 2 In Progress  
**Target Implementation Model:** Claude Sonnet 4.6  
**Repository Visibility:** Public  
**Versioning:** Semantic Versioning  

** Main Local Project Folder Location **
D:\REPOS\MCP_SERVERS\PYRIT-MCP on Windows filesystem
---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Core Concept & Value Proposition](#2-core-concept--value-proposition)
3. [Architecture Overview](#3-architecture-overview)
4. [Technology Stack](#4-technology-stack)
5. [Directory Structure](#5-directory-structure)
6. [Tool Domain Specifications](#6-tool-domain-specifications)
7. [LLM Backend Architecture](#7-llm-backend-architecture)
8. [RAM-Tiered Model Selection](#8-ram-tiered-model-selection)
9. [Docker Architecture](#9-docker-architecture)
10. [GitHub Repository Architecture](#10-github-repository-architecture)
11. [System Detection & Model Recommendation](#11-system-detection--model-recommendation)
12. [Configuration Architecture](#12-configuration-architecture)
13. [Linux Bare Metal Optimizations](#13-linux-bare-metal-optimizations)
14. [Makefile Specification](#14-makefile-specification)
15. [Session & State Model](#15-session--state-model)
16. [Security Considerations](#16-security-considerations)
17. [Phased Build Plan](#17-phased-build-plan)
18. [Open Design Decisions](#18-open-design-decisions)
19. [Coding Instructions for Claude](#19-coding-instructions-for-claude)

---

## 1. Project Overview

### 1.1 Identity

| Field | Value |
|---|---|
| **Project Name** | `pyrit-mcp` |
| **Repository** | Public GitHub repository |
| **Container Registry** | GitHub Container Registry (ghcr.io) |
| **Versioning** | Semantic Versioning (v1.0.0, v1.1.0, etc.) |
| **MCP Transport** | stdio (local server) |
| **Primary Language** | Python 3.11 |
| **MCP Framework** | FastMCP |
| **Target Clients** | Claude Desktop, Claude Code, any MCP-compatible LLM client |

### 1.2 What This Is

An MCP (Model Context Protocol) server that wraps **Microsoft's PyRIT** (Python Risk Identification Toolkit), exposing its AI red-teaming capabilities as structured tools that Claude — or any MCP-compatible LLM — can orchestrate, direct, and reason about in real time.

The server transforms PyRIT from a static CLI tool into an **intelligent, LLM-orchestrated red-team platform**. Claude acts as the test director: choosing attack strategies, interpreting results, generating follow-up probes, and writing structured reports — all through a clean tool interface.

### 1.3 Why This Matters

- **PyRIT alone** runs static scripts and logs results to a database
- **PyRIT + MCP** gives an LLM the ability to reason about results, adapt strategies mid-campaign, and produce structured vulnerability reports
- **No equivalent tool exists** in the current MCP ecosystem
- **Target users:** AI product teams, security red teams, security consultants, compliance teams, AI safety researchers

---

## 2. Core Concept & Value Proposition

### 2.1 The Fundamental Tension PyRIT Addresses

PyRIT requires two LLM roles with opposing safety requirements:

| Role | Job | Safety Requirement |
|---|---|---|
| **Attacker LLM** | Generates adversarial prompts, jailbreaks, escalating multi-turn attacks | Must be **uncensored** — safety-filtered models refuse to generate attack content |
| **Scorer LLM** | Judges whether a target response contains harmful content | Can be safety-filtered — it is evaluating, not generating attacks |

A safety-filtered model (GPT-4, Claude) used as an attacker will refuse its job. The architecture must support fully uncensored local models as attackers while allowing high-quality filtered models as scorers. These two backends are independently configurable at all times.

### 2.2 Value Delivered

| Dimension | Value |
|---|---|
| **Speed** | Compress days of manual red-teaming into hours |
| **Coverage** | Systematic coverage of PyRIT's 1,400+ built-in attack prompts across harm categories |
| **Intelligence** | Claude reasons about why an attack succeeded and suggests follow-up probes |
| **Repeatability** | Same test suite runs against new model versions automatically |
| **Reporting** | Auto-generate structured vulnerability reports with remediation suggestions |
| **Extensibility** | Custom datasets, scorers, and converters for domain-specific testing |
| **Cost** | Fully offline operation possible with local LLMs — zero API costs |
| **Privacy** | Sensitive red-team prompts never leave the local machine |

---

## 3. Architecture Overview

### 3.1 System Topology

```
Claude Desktop / Claude Code / Any MCP Client
         |
         | MCP stdio transport
         v
+---------------------------------------------+
|            PyRIT MCP Server                 |
|         (FastMCP, Python 3.11)              |
|                                             |
|  +----------+  +----------+  +----------+  |
|  | Targets  |  |Orchestr. |  | Scorers  |  |
|  +----------+  +----------+  +----------+  |
|  +----------+  +----------+  +----------+  |
|  | Datasets |  |Converters|  | Results  |  |
|  +----------+  +----------+  +----------+  |
|  +--------------------------------------+  |
|  |         Backend Manager              |  |
|  |  (Attacker Config | Scorer Config)   |  |
|  +--------------------------------------+  |
|  +--------------------------------------+  |
|  |           DuckDB Session             |  |
|  +--------------------------------------+  |
+-------------------+--------------------------+
                    |
          +---------+---------+
          v                   v
     ATTACKER LLM         SCORER LLM
     (Uncensored)         (Any quality)
          |                   |
   +------+------+     +------+------+
   | Ollama      |     |  GPT-4o     |
   | llama.cpp   |     |  Azure OAI  |
   | Groq          |
              TARGET APP
         (The AI being tested)
```
    |     |  Ollama     |
   +-------------+     +-------------+
              
### 3.2 Dual-Backend Independence

Attacker and Scorer are **independently configurable** at all times. They can use different providers, different models, different quantization levels, and different instances. This is a hard architectural requirement — they must never be assumed to be the same model or provider.

---

## 4. Technology Stack

### 4.1 Core Dependencies

| Component | Technology | Rationale |
|---|---|---|
| MCP Framework | FastMCP | Cleanest Python MCP pattern; idiomatic decorator-based tool registration |
| Language | Python 3.11 | PyRIT is Python-only; 3.11 for performance improvements |
| Red-team Framework | Microsoft PyRIT (`pip install pyrit`) | The core library being wrapped |
| Database | DuckDB | PyRIT's native session store; fast, embedded, no server required |
| Input Validation | Pydantic | Schema validation for all tool inputs and outputs |
| Config Management | python-dotenv | Environment variable loading |
| Async Runtime | asyncio (stdlib) | All I/O operations are non-blocking |

### 4.2 LLM Backends Supported

| Backend | Use Case | API Interface |
|---|---|---|
| Ollama | Local models, CPU and GPU, easiest setup | OpenAI-compatible REST |
| llama.cpp server | Direct high-performance inference, large models, bare metal | OpenAI-compatible REST |
| Azure OpenAI | Enterprise, compliance-gated environments | Azure SDK |
| OpenAI API | Scorer LLM; not recommended for attacker role | OpenAI SDK |
| Groq API | Speed-sensitive scoring workloads | OpenAI-compatible REST |
| HuggingFace TGI | Custom fine-tuned attack models | OpenAI-compatible REST |

### 4.3 Infrastructure

| Component | Technology |
|---|---|
| Containerization | Docker (multi-stage, multi-platform linux/amd64 + linux/arm64) |
| Local Orchestration | Docker Compose with named profiles |
| Image Registry | GitHub Container Registry (ghcr.io) |
| CI/CD | GitHub Actions (3 workflows) |
| Linting and Formatting | ruff |
| Type Checking | mypy |
| Pre-commit Framework | pre-commit |
| Secret Detection | detect-secrets |
| Dockerfile Linting | hadolint |

### 4.4 Development Tooling

| Component | Technology |
|---|---|
| Package Metadata | pyproject.toml |
| Test Framework | pytest |
| Dev Dependencies | pytest, ruff, mypy, ipython, watchdog |
| Model Downloads | huggingface-cli (huggingface_hub package) |
| Developer UX | Makefile (all common commands) |

---

## 5. Directory Structure

```
pyrit-mcp/
|
+-- .github/
|   +-- workflows/
|   |   +-- ci.yml                    # Lint + typecheck + test on every PR
|   |   +-- build-and-push.yml        # Multi-platform Docker build on merge to main
|   |   +-- release.yml               # Tag-triggered versioned release
|   +-- ISSUE_TEMPLATE/
|   |   +-- bug_report.md
|   |   +-- feature_request.md
|   +-- pull_request_template.md
|
+-- pyrit_mcp/
|   +-- __init__.py                   # Package init, version string
|   +-- server.py                     # FastMCP entry point, all tool registration
|   +-- config.py                     # ServerConfig, BackendConfig, env loading
|   +-- tools/
|   |   +-- __init__.py               # Exports all tools for server.py to import
|   |   +-- targets.py                # Domain 1: Target management
|   |   +-- orchestrators.py          # Domain 2: Attack orchestration
|   |   +-- datasets.py               # Domain 3: Dataset and prompt libraries
|   |   +-- scorers.py                # Domain 4: Scoring and evaluation
|   |   +-- converters.py             # Domain 5: Prompt conversion/obfuscation
|   |   +-- results.py                # Domain 6: Result storage and reporting
|   |   +-- backends.py               # Domain 7: Backend configuration and management
|   +-- utils/
|       +-- __init__.py
|       +-- rate_limiter.py           # Token bucket rate limiter
|       +-- db.py                     # DuckDB singleton connection and schema init
|       +-- formatters.py             # Structured JSON output helpers
|       +-- system_detect.py          # Python wrapper for detect_system.sh output
|
+-- tests/
|   +-- conftest.py                   # Shared pytest fixtures and configuration
|   +-- test_targets.py
|   +-- test_orchestrators.py
|   +-- test_scorers.py
|   +-- test_backends.py
|   +-- test_converters.py
|   +-- test_results.py
|   +-- test_system_detect.py
|
+-- evaluations/
|   +-- eval_questions.xml            # 10 MCP evaluation QA pairs
|
+-- docker/
|   +-- Dockerfile                    # Production MCP server image
|   +-- Dockerfile.dev                # Dev image: hot reload, debug tools
|   +-- Dockerfile.scorer             # HuggingFace classifier sidecar
|   +-- entrypoint.sh                 # Startup: env validation, db init, server launch
|
+-- scripts/
|   +-- detect_system.sh              # Core RAM/GPU/CPU/NUMA hardware detection
|   +-- recommend_models.sh           # Model recommendation engine
|   +-- download_model.sh             # HuggingFace GGUF downloader
|   +-- validate_env.sh               # Pre-flight environment check
|   +-- benchmark.sh                  # Inference speed tester
|
+-- config/
|   +-- model_catalog.json            # Machine-readable model registry
|   +-- tier_profiles.json            # RAM tier to recommended config mapping
|
+-- models/                           # GITIGNORED — GGUF model files live here
|   +-- .gitkeep
|
+-- data/                             # GITIGNORED — DuckDB session database
|   +-- .gitkeep
|
+-- docker-compose.yml                # Full compose stack with all profiles
+-- docker-compose.dev.yml            # Dev override: volume mounts, debug ports
+-- Makefile                          # All developer and operator commands
+-- pyproject.toml                    # Package metadata and tool configuration
+-- requirements.txt                  # Production dependencies (pinned)
+-- requirements-dev.txt              # Dev dependencies
+-- .env.example                      # Template for all env vars with documentation
+-- .env.docker.example               # Docker-specific env var template
+-- .env.detected                     # GITIGNORED — written by make detect
+-- .dockerignore
+-- .gitignore
+-- .pre-commit-config.yaml
+-- CHANGELOG.md
+-- CONTRIBUTING.md
+-- LICENSE
+-- README.md
```

---

## 6. Tool Domain Specifications

### Universal Tool Rules

- All tools return structured JSON dicts — never prose strings
- All I/O operations are async/await — no blocking calls anywhere
- Every tool declares `readOnlyHint`, `destructiveHint`, `idempotentHint` annotations
- Error messages always include a `suggestion` field that tells Claude what tool to call next
- Destructive tools require a `confirm: true` parameter before executing
- Credentials are only accepted as env var names, never as raw values

---

### Domain 1 — Target Management (`tools/targets.py`)

Configure what application is being tested.

| Tool | Description | Key Parameters | Annotations |
|---|---|---|---|
| `pyrit_configure_http_target` | Register an HTTP endpoint as a target | `url`, `headers`, `request_template`, `response_path` | destructive: false |
| `pyrit_configure_openai_target` | Register an OpenAI-compatible endpoint | `api_base`, `api_key_env`, `model`, `system_prompt` | destructive: false |
| `pyrit_configure_azure_target` | Register an Azure OpenAI deployment | `deployment_name`, `endpoint`, `api_version` | destructive: false |
| `pyrit_list_targets` | List all configured targets in this session | — | readOnly: true |
| `pyrit_remove_target` | Remove a target by ID | `target_id`, `confirm: true` | destructive: true |
| `pyrit_test_target_connectivity` | Verify target responds to a probe | `target_id`, `probe_prompt` | readOnly: true |

**Security constraint:** Tool parameters only accept env var names for credentials, never actual keys. This keeps secrets out of MCP conversation logs.

---

### Domain 2 — Attack Orchestration (`tools/orchestrators.py`)

Run red-team attack campaigns.

| Tool | Description | Key Parameters | Annotations |
|---|---|---|---|
| `pyrit_run_prompt_sending_orchestrator` | Fire a dataset at a target | `target_id`, `dataset_name`, `max_requests`, `requests_per_second` | destructive: true |
| `pyrit_run_crescendo_orchestrator` | Multi-turn escalating attack | `target_id`, `attack_goal`, `max_turns`, `scorer_id` | destructive: true |
| `pyrit_run_pair_orchestrator` | Prompt Automatic Iterative Refinement | `target_id`, `attack_goal`, `attacker_model`, `max_iterations` | destructive: true |
| `pyrit_run_tree_of_attacks_orchestrator` | TAP branching attack tree | `target_id`, `attack_goal`, `branching_factor`, `depth` | destructive: true |
| `pyrit_run_skeleton_key_orchestrator` | Skeleton key jailbreak technique | `target_id`, `unlock_prompt`, `follow_up_prompt` | destructive: true |
| `pyrit_run_flip_orchestrator` | FLIP attack variant | `target_id`, `dataset_name` | destructive: true |
| `pyrit_cancel_attack` | Stop a running attack campaign | `attack_id` | destructive: true |
| `pyrit_get_attack_status` | Poll progress on a running campaign | `attack_id` | readOnly: true |

**Critical async pattern:** Every orchestrator returns an `attack_id` string immediately and runs the attack in the background. Status is polled separately via `pyrit_get_attack_status`. This prevents MCP tool timeout on long campaigns. Never block the tool call waiting for attack completion.

---

### Domain 3 — Datasets & Prompt Libraries (`tools/datasets.py`)

Manage the adversarial prompt inventory.

| Tool | Description | Key Parameters | Annotations |
|---|---|---|---|
| `pyrit_list_builtin_datasets` | List all PyRIT built-in harm datasets | `filter_category` | readOnly: true |
| `pyrit_load_dataset` | Load a named dataset into this session | `dataset_name`, `max_samples`, `shuffle` | idempotent: true |
| `pyrit_preview_dataset` | Show sample prompts from a dataset | `dataset_name`, `n_samples` | readOnly: true |
| `pyrit_create_custom_dataset` | Upload a list of custom prompts | `prompts`, `category`, `dataset_name` | destructive: false |
| `pyrit_import_dataset_from_file` | Load prompts from a local CSV or JSON file | `file_path`, `prompt_column`, `category` | destructive: false |
| `pyrit_list_session_datasets` | Show all datasets loaded in this session | — | readOnly: true |
| `pyrit_merge_datasets` | Combine multiple datasets into one | `dataset_names`, `output_name`, `deduplicate` | destructive: false |

**Built-in dataset categories exposed:**
`violence`, `hate`, `self-harm`, `sexual`, `illegal-weapons`, `drug-synthesis`, `cybercrime`, `political-extremism`, `privacy-violation`, `jailbreak-classic`, `jailbreak-roleplay`, `prompt-injection`

---

### Domain 4 — Scorers (`tools/scorers.py`)

Evaluate whether an attack succeeded.

| Tool | Description | Key Parameters | Annotations |
|---|---|---|---|
| `pyrit_configure_llm_scorer` | Set up an LLM-as-judge scorer | `model`, `api_key_env`, `scoring_task`, `scale` | destructive: false |
| `pyrit_configure_substring_scorer` | Score by keyword presence | `keywords`, `match_mode` (any/all/regex) | destructive: false |
| `pyrit_configure_classifier_scorer` | Use a local harm classifier model | `model_path_or_name`, `categories` | destructive: false |
| `pyrit_score_response` | Score a single response text | `response_text`, `scorer_id`, `context` | readOnly: true |
| `pyrit_score_attack_results` | Batch-score all results from an attack | `attack_id`, `scorer_id` | destructive: false |
| `pyrit_list_scorers` | List all configured scorers | — | readOnly: true |
| `pyrit_get_score_distribution` | Aggregate score statistics for an attack | `attack_id`, `scorer_id` | readOnly: true |

**Cost guard requirement:** The LLM scorer (e.g., GPT-4o as judge) is expensive. Before executing `pyrit_score_attack_results` with an LLM scorer, the tool must:
1. Estimate the token count and cost
2. Return the estimate with status `"pending_confirmation"`
3. Require the caller to pass `confirm_cost: true` to proceed

---

### Domain 5 — Results & Reporting (`tools/results.py`)

Query, filter, and export red-team findings.

| Tool | Description | Key Parameters | Annotations |
|---|---|---|---|
| `pyrit_list_attacks` | List all attacks in this session | `target_id`, `status_filter` | readOnly: true |
| `pyrit_get_attack_results` | Retrieve raw results for an attack | `attack_id`, `filter_score_min`, `limit`, `offset` | readOnly: true |
| `pyrit_get_successful_jailbreaks` | Return only successful bypass responses | `attack_id`, `scorer_id`, `score_threshold` | readOnly: true |
| `pyrit_get_failed_attacks` | Return prompts that were refused | `attack_id` | readOnly: true |
| `pyrit_export_results_csv` | Export results to a CSV file | `attack_id`, `output_path` | destructive: false |
| `pyrit_generate_report` | Return structured JSON for Claude to narrate as a report | `attack_id`, `format` | readOnly: true |
| `pyrit_compare_attacks` | Diff results between two attack runs | `attack_id_a`, `attack_id_b` | readOnly: true |
| `pyrit_clear_session` | Wipe all session data from DuckDB | `confirm: true` | destructive: true |

**Architecture note on `pyrit_generate_report`:** This tool returns raw structured JSON data only. Claude (the MCP client) writes the actual report narrative from that data. This avoids circular LLM dependencies and keeps the report generation within Claude's context window where it can reason about it.

---

### Domain 6 — Converters (`tools/converters.py`)

Transform prompts before sending to apply obfuscation or framing.

| Tool | Description | Key Parameters |
|---|---|---|
| `pyrit_list_converters` | List all available converters with descriptions | — |
| `pyrit_apply_converter` | Apply a single converter to a prompt or dataset | `converter_name`, `input` (prompt string or dataset_name) |
| `pyrit_chain_converters` | Apply a sequence of converters in order | `converter_names` (ordered list), `input` |

**Built-in converters:**
`base64`, `rot13`, `leetspeak`, `unicode_substitution`, `morse_code`, `caesar_cipher`, `language_translation`, `tone_academic`, `tone_fictional`, `suffix_injection`, `prefix_injection`, `character_space_insertion`

---

### Domain 7 — Backend Management (`tools/backends.py`)

Configure, switch, and manage LLM backends at runtime.

| Tool | Description | Key Parameters |
|---|---|---|
| `pyrit_configure_attacker_backend` | Switch the attacker LLM | `backend_type`, `model`, `base_url`, `api_key_env` |
| `pyrit_configure_scorer_backend` | Switch the scorer LLM | `backend_type`, `model`, `api_key_env` |
| `pyrit_list_backend_options` | Show available backends and connectivity status | — |
| `pyrit_test_backend_connectivity` | Verify a backend responds to a probe | `backend_role` (attacker or scorer) |
| `pyrit_estimate_attack_cost` | Estimate token cost before running attack | `attack_id`, `backend_type` |
| `pyrit_recommend_models` | Return ranked model recommendations for this hardware | `available_ram_gb`, `has_gpu`, `gpu_vram_gb`, `role` |
| `pyrit_pull_ollama_model` | Pull a model into Ollama at runtime | `model_name`, `confirm_size_gb` |
| `pyrit_list_ollama_models` | List models currently available in Ollama | — |
| `pyrit_benchmark_backend` | Run inference speed test on a configured backend | `backend_role`, `n_tokens` |

---

## 7. LLM Backend Architecture

### 7.1 Attacker LLM Backend Options

| Backend | Cost | Privacy | Uncensored | Complexity | Recommendation |
|---|---|---|---|---|---|
| **Ollama (local)** | Free | Total | Full control | Low | Default for all tiers |
| **llama.cpp direct** | Free | Total | Full control | Medium | Best for Tier 5/6/7 |
| **Azure OpenAI (Foundry)** | Pay-per-token | Azure tenant only | Partial (filtered) | Medium | Enterprise/compliance environments |
| **OpenAI API** | Pay-per-token | Sent to OpenAI | Filtered | Low | **Not recommended for attacker role** |
| **Groq API** | Pay-per-token | Sent to Groq | Partial | Low | Speed-sensitive use cases |
| **HuggingFace TGI** | Free/paid | Self-hosted | Full control | High | Custom fine-tuned attack models |

### 7.2 Scorer LLM Backend Options

| Backend | Quality | Cost | Best Use Case |
|---|---|---|---|
| **OpenAI GPT-4o** | Highest | Pay-per-token | Standard scorer choice |
| **Azure OpenAI GPT-4** | High | Pay-per-token | Enterprise compliance requirement |
| **Ollama (local)** | Medium | Free | Fully offline operation |
| **Substring/Classifier** | Deterministic | Free | Fast, cheap, no LLM required |

### 7.3 Azure Foundry Special Handling

Azure OpenAI is still content-filtered at the API layer by default. Microsoft offers a **Limited Access content filter bypass** program specifically for red-teaming use cases within Azure AI Foundry:

- Must apply for the Limited Access program for unrestricted content generation
- Available under the Azure AI safety evaluation service
- Requires signing Microsoft's responsible use agreement
- Best path for enterprise teams that cannot use local Ollama for compliance reasons

**Implementation requirement:** The Azure backend config needs an optional `content_filter_override: bool` flag that sets the appropriate Azure API request headers when Limited Access enrollment is confirmed.

### 7.4 llama.cpp Direct Backend

#### Why Direct llama.cpp vs Ollama

| Feature | Ollama | llama.cpp direct |
|---|---|---|
| Performance overhead | ~15-20% | Minimal |
| API surface | OpenAI-compatible REST | OpenAI-compatible REST (server mode) |
| Thread count control | ENV var only | Full granular control |
| Batch size tuning | Limited | Full control |
| Context window | Capped by config | Full control |
| Memory mapping | Automatic | Explicit mmap and mlock control |
| 405B FP16 inference | Struggles | Native — designed for this |
| Multi-GPU tensor parallel | Limited | Full support |
| NUMA topology awareness | None | `--numa distribute` flag |

For Tier 5/6/7 (256GB+ RAM), performance differences on large models justify the added complexity.

#### llama.cpp Docker Image

Use the official maintained image: `ghcr.io/ggerganov/llama.cpp:server`

#### Runtime Configuration Flags (all mapped to ENV vars)

| ENV Var | llama.cpp Flag | Purpose |
|---|---|---|
| `LLAMACPP_MODEL_PATH` | `--model` | Path to GGUF file inside container |
| `LLAMACPP_N_GPU_LAYERS` | `--n-gpu-layers` | Layers to GPU (0 = CPU only, -1 = all) |
| `LLAMACPP_N_THREADS` | `--threads` | CPU threads (use physical cores, not hyperthreaded count) |
| `LLAMACPP_CTX_SIZE` | `--ctx-size` | Context window (32768 recommended for red-teaming) |
| `LLAMACPP_BATCH_SIZE` | `--batch-size` | Prompt evaluation batch size (512-2048) |
| `LLAMACPP_UBATCH_SIZE` | `--ubatch-size` | Micro-batch size for generation |
| `LLAMACPP_N_PARALLEL` | `--parallel` | Concurrent request slots |
| `LLAMACPP_MLOCK` | `--mlock` | Lock model in RAM, prevent swapping (set true for large models) |
| `LLAMACPP_MMAP` | `--mmap` | Memory-map model file for faster startup |
| `LLAMACPP_NUMA` | `--numa` | NUMA optimization mode (use `distribute` for dual-socket) |
| `LLAMACPP_PORT` | `--port` | Server port (default 8080) |
| `LLAMACPP_HOST` | `--host` | Bind address |

#### CRITICAL: NUMA for Dual-Socket Machines

On any dual-socket EPYC, Threadripper, or Xeon system, `--numa distribute` is mandatory. Without NUMA awareness, llama.cpp incurs heavy cross-socket memory bus penalties as threads fetch data from the remote NUMA node. With `--numa distribute`, model layers are spread proportionally across both NUMA nodes. This difference can be **2-3x throughput** on large models.

`detect_system.sh` runs `numactl --hardware` to detect socket and NUMA topology and sets this flag automatically in `.env.detected`.

#### GGUF Model File Volume Strategy

GGUF model files are too large to download inside a container build. The design:

```
Host filesystem: /path/to/pyrit-mcp/models/
  +-- llama3.1-405b-Q8_0.gguf       (downloaded once to host, persists)
  +-- llama3.1-70b-Q6_K.gguf
  +-- dolphin-mixtral-8x22b-Q4.gguf

Docker volume mount:
  host: ./models -> container: /models (read-only bind mount)
```

`make download-model MODEL=llama3.1:405b QUANT=Q8_0` handles the download workflow:
1. Looks up model in `config/model_catalog.json` for exact filename and HuggingFace repo
2. Calculates required disk space
3. Prompts user for confirmation before downloading
4. Downloads via `huggingface-cli download`
5. Places file in `./models/` directory
6. Updates `.env.detected` with the model path

---

## 8. RAM-Tiered Model Selection

### 8.1 Quantization Reference Table

| Quantization | RAM vs FP16 | Quality vs FP16 | Best Use |
|---|---|---|---|
| `FP16` | 1.0x baseline | None | Scorer on Tier 7 systems |
| `Q8_0` | ~0.50x | Negligible | Attacker on Tier 7 (512GB+) |
| `Q6_K` | ~0.375x | Minimal | Attacker Tier 6, Scorer Tier 5 |
| `Q5_K_M` | ~0.31x | Small | Attacker Tier 5 (128-256GB) |
| `Q5_K_S` | ~0.30x | Small | Slightly smaller Q5 variant |
| `Q4_K_M` | ~0.25x | Moderate | Default for Tiers 1-4 |
| `Q4_K_S` | ~0.24x | Moderate | Tight RAM budget |
| `Q3_K_M` | ~0.19x | Noticeable | Emergency fit only |
| `Q2_K` | ~0.13x | Significant | Absolute minimum, last resort |

### 8.2 Tier Definitions and Model Recommendations

#### Tier 1 — 8-16GB RAM

**Capability:** Basic prompt injection and dataset attack testing. Substring scorer only. Crescendo and PAIR not viable at this tier.

| Role | Model | Quant | RAM Required | Backend | Profile |
|---|---|---|---|---|---|
| Attacker | `dolphin-mistral` (7B) | Q4_K_M | ~4GB | Ollama | `local-llm` |
| Scorer | Substring scorer | N/A | 0GB | Built-in | — |
| Fallback | `tinydolphin` (1.1B) | Q4_K_M | ~0.6GB | Ollama | — |

---

#### Tier 2 — 17-31GB RAM

**Capability:** Most single-turn orchestrators viable. Basic Crescendo works with quality tradeoffs.

| Role | Model | Quant | RAM Required | Backend | Profile |
|---|---|---|---|---|---|
| Attacker | `dolphin-mixtral:8x7b` (47B MoE) | Q4_K_M | ~26GB | Ollama | `local-llm` |
| Scorer | Substring or `toxic-bert` classifier | N/A | ~1GB | Sidecar | `local-scorer` |
| Alternatives | `wizard-vicuna-uncensored` (13B), `nous-hermes2` (11B) | Q4_K_M | 7-11GB | Ollama | — |

---

#### Tier 3 — 32-63GB RAM

**Capability:** Full orchestrator suite. Crescendo and PAIR both viable. Dual-instance attacker and scorer.

| Role | Model | Quant | RAM Required | Backend | Profile |
|---|---|---|---|---|---|
| Attacker | `dolphin-mixtral:8x22b` (141B MoE) | Q4_K_M | ~48GB | Ollama | `dual-ollama` |
| Scorer | `nous-hermes2` (7B) | Q4_K_M | ~7GB | Ollama (separate instance) | `dual-ollama` |
| Alternatives | `wizardlm2:8x22b`, `goliath-120b` | Q4_K_M | varies | Ollama | — |

---

#### Tier 4 — 64-127GB RAM

**Capability:** High-quality multi-turn attacks. Tree-of-Attacks viable. Suitable for most professional engagements.

| Role | Model | Quant | RAM Required | Backend | Profile |
|---|---|---|---|---|---|
| Attacker (preferred) | `dolphin-mixtral:8x22b` | Q6_K | ~58GB | Ollama | `dual-ollama` |
| Attacker (max quality) | `llama3.1:405b` | Q2_K | ~100GB | Ollama | `dual-ollama` |
| Scorer | `llama3.1:70b` | Q4_K_M | ~40GB | Ollama (separate) | `dual-ollama` |

**Warning:** When selecting `llama3.1:405b` at Q2_K, the tool response must document the quality tradeoff explicitly.

---

#### Tier 5 — 128-255GB RAM

**Capability:** Near-frontier attack quality. Suitable for high-value AI application testing.

| Role | Model | Quant | RAM Required | Backend | Profile |
|---|---|---|---|---|---|
| Attacker | `llama3.1:405b` | Q4_K_M | ~220GB | Ollama or llama.cpp | `full-llamacpp` |
| Scorer | `llama3.1:70b` | Q8_0 | ~70GB | Ollama | `full-llamacpp` |

---

#### Tier 6 — 256-511GB RAM

**Capability:** Frontier-adjacent open-weight performance. Attacks approach GPT-4 quality with no content filtering.

| Role | Model | Quant | RAM Required | Backend | Profile |
|---|---|---|---|---|---|
| Attacker | `llama3.1:405b` | Q5_K_M | ~265GB | llama.cpp direct | `full-llamacpp` |
| Scorer | `llama3.1:70b` | Q8_0 | ~70GB | Ollama | `full-llamacpp` |

---

#### Tier 7 — 512GB-768GB RAM (e.g., project owner's 768GB inference workstation)

**Capability:** Professional AI security research grade. Running `llama3.1:405b` at Q8_0 locally with no content filtering exceeds the attacker quality of most commercial red-team platforms. Can run attacker and scorer simultaneously with significant RAM headroom remaining.

| Role | Model | Quant | RAM Required | Backend | Profile |
|---|---|---|---|---|---|
| Attacker | `llama3.1:405b` | Q8_0 | ~400GB | llama.cpp direct | `full-llamacpp` |
| Scorer | `llama3.1:70b` | FP16 | ~140GB | Ollama | `full-llamacpp` |
| Headroom | ~228GB remaining | — | Optional third specialized model | — | — |

**Special Tier 7 capability:** The remaining ~228GB RAM can host a third model for specialized attack domains (e.g., a domain-specific fine-tuned attacker for medical, legal, or cybersecurity topics).

**Note:** True FP16 inference for 405B requires 810GB+ RAM. Q8_0 at ~400GB is the practical maximum quality reachable at the 768GB tier.

---

### 8.3 Recommended Uncensored Model Catalog

| Model | Params | Family | Why Good for Attacking | Ollama Pull Name |
|---|---|---|---|---|
| `dolphin-mistral` | 7B | Mistral | Dolphin series removes safety training; strong instruction following | `dolphin-mistral` |
| `dolphin-mixtral:8x7b` | 47B MoE | Mixtral | Best uncensored at 26-32GB tier | `dolphin-mixtral:8x7b` |
| `dolphin-mixtral:8x22b` | 141B MoE | Mixtral | Flagship uncensored MoE; excellent attacker quality | `dolphin-mixtral:8x22b` |
| `wizard-vicuna-uncensored` | 13B | LLaMA | Purpose-built for unconstrained output generation | `wizard-vicuna-uncensored` |
| `nous-hermes2` | 11B | Mistral | Strong reasoning, minimal refusals | `nous-hermes2` |
| `nous-hermes-2-mixtral-8x7b` | 47B MoE | Mixtral | Fast, good quality, minimal refusals | `nous-hermes2-mixtral-8x7b` |
| `mistral-nemo` | 12B | Mistral | Strong reasoning, less filtered than base Mistral | `mistral-nemo` |
| `llama3.1:405b` | 405B | LLaMA 3 | Best open-weight model; practically uncensored at high quant | `llama3.1:405b` |

---

## 9. Docker Architecture

### 9.1 Production Image (`docker/Dockerfile`)

**Base image:** `python:3.11-slim`

**Rationale for slim over alpine:** PyRIT has compiled dependencies (numpy, duckdb) that require glibc. Alpine Linux causes significant build failures with these dependencies.

**Layer build order (optimized for Docker cache efficiency):**

```
Layer 1 — OS system dependencies   apt: gcc, libgomp (numpy), build tools
Layer 2 — Python pip dependencies  requirements.txt — cache only busts on dep changes
Layer 3 — PyRIT installation       large package, separate layer
Layer 4 — Application code         pyrit_mcp/ — changes most frequently
Layer 5 — Entrypoint               entrypoint.sh
```

**Security baseline:**
- Server runs as non-root user `pyrit` (uid 1000)
- No secrets baked into any image layer

**Volumes:**
- `/data` — DuckDB session database (bind mount from host for persistence)
- `/datasets` — Optional custom dataset CSV/JSON files
- `/models` — GGUF model files (read-only bind mount)

### 9.2 Dev Image (`docker/Dockerfile.dev`)

Extends production image with:
- `requirements-dev.txt` (pytest, ruff, mypy, ipython)
- Source code volume-mounted for hot reload without rebuilds
- `watchdog` package for filesystem monitoring
- Debug port exposed

### 9.3 Scorer Sidecar (`docker/Dockerfile.scorer`)

Lightweight HuggingFace harm classifier:
- Default models: `unitary/toxic-bert` or `martin-ha/toxic-comment-model`
- Exposes a simple REST scoring endpoint
- PyRIT's HTTP scorer interface consumes this endpoint
- Used in `local-scorer` and `full` compose profiles

### 9.4 `entrypoint.sh` Execution Order

1. Source `.env` file if present
2. Validate required ENV vars are set — exit with descriptive error if any are missing
3. Initialize DuckDB database file at `$PYRIT_DB_PATH` if it does not exist
4. Log the active configuration summary (backend types, models, sandbox mode status)
5. Execute `python -m pyrit_mcp.server` to start the FastMCP server

### 9.5 Compose Profile Definitions

| Profile Flag | Services Started | Intended Use |
|---|---|---|
| *(no profile)* | `pyrit-mcp` only | External LLM via ENV vars; cloud backends |
| `local-llm` | `pyrit-mcp` + `ollama` + `ollama-init` | CPU-only local inference |
| `local-llm-gpu` | `pyrit-mcp` + `ollama-gpu` + `ollama-init` | NVIDIA GPU-accelerated inference |
| `local-llm-amd` | `pyrit-mcp` + `ollama-amd` + `ollama-init` | AMD ROCm GPU inference |
| `local-scorer` | `pyrit-mcp` + `pyrit-scorer` | Local HuggingFace classifier scorer |
| `dual-ollama` | `pyrit-mcp` + `ollama` + `ollama-scorer` + both init containers | Independent attacker/scorer instances |
| `full` | All CPU services combined | Fully offline CPU-only stack |
| `full-gpu` | All services with NVIDIA GPU | Fully offline GPU-accelerated stack |
| `full-llamacpp` | `pyrit-mcp` + `llamacpp-attacker` + `ollama-scorer` | Tier 5/6/7 high-RAM configuration |

### 9.6 Service Definitions Detail

#### `ollama` service (profile: `local-llm`)
```yaml
image: ollama/ollama:latest
volumes:
  - ollama-models:/root/.ollama
environment:
  OLLAMA_NUM_PARALLEL: ${OLLAMA_NUM_PARALLEL:-1}
  OLLAMA_MAX_LOADED_MODELS: ${OLLAMA_MAX_LOADED_MODELS:-1}
  OLLAMA_FLASH_ATTENTION: ${OLLAMA_FLASH_ATTENTION:-false}
  OLLAMA_KV_CACHE_TYPE: ${OLLAMA_KV_CACHE_TYPE:-q8_0}
  OLLAMA_NUM_THREADS: ${OLLAMA_NUM_THREADS:-4}
  OLLAMA_RUNNER_NUMCTX: ${OLLAMA_RUNNER_NUMCTX:-2048}
```

#### `ollama-gpu` service (profile: `local-llm-gpu`)
Extends `ollama` service and adds NVIDIA device reservation:
```yaml
deploy:
  resources:
    reservations:
      devices:
        - driver: nvidia
          count: all
          capabilities: [gpu]
environment:
  NVIDIA_VISIBLE_DEVICES: all
  CUDA_VISIBLE_DEVICES: ${CUDA_VISIBLE_DEVICES:-all}
```
Requires `nvidia-container-toolkit` installed on host. README documents the installation procedure.

#### `ollama-amd` service (profile: `local-llm-amd`)
```yaml
image: ollama/ollama:rocm
devices:
  - /dev/kfd
  - /dev/dri
environment:
  HSA_OVERRIDE_GFX_VERSION: ${HSA_OVERRIDE_GFX_VERSION:-}
```

#### `ollama-init` service (all Ollama profiles)
One-shot init container that pulls the configured attacker model:
```yaml
restart: "no"
depends_on:
  ollama:
    condition: service_healthy
command: ["ollama", "pull", "${OLLAMA_MODEL}"]
```

#### `ollama-scorer` service (profile: `dual-ollama`)
Second independent Ollama instance on port 11435:
- Pulls `$OLLAMA_SCORER_MODEL` independently from attacker model
- Allows running `dolphin-mixtral:8x22b` as attacker and `llama3.1:70b` as scorer simultaneously
- Critical design for Tier 3+ deployments

#### `llamacpp-attacker` service (profile: `full-llamacpp`)
```yaml
image: ghcr.io/ggerganov/llama.cpp:server
volumes:
  - ./models:/models:ro
environment:
  LLAMACPP_MODEL_PATH: ${LLAMACPP_MODEL_PATH}
  LLAMACPP_N_THREADS: ${LLAMACPP_N_THREADS:-8}
  LLAMACPP_CTX_SIZE: ${LLAMACPP_CTX_SIZE:-32768}
  LLAMACPP_BATCH_SIZE: ${LLAMACPP_BATCH_SIZE:-512}
  LLAMACPP_MLOCK: ${LLAMACPP_MLOCK:-false}
  LLAMACPP_MMAP: ${LLAMACPP_MMAP:-true}
  LLAMACPP_NUMA: ${LLAMACPP_NUMA:-}
  LLAMACPP_N_PARALLEL: ${LLAMACPP_N_PARALLEL:-4}
  LLAMACPP_N_GPU_LAYERS: ${LLAMACPP_N_GPU_LAYERS:-0}
```

### 9.7 Named Volumes

```yaml
volumes:
  pyrit-db:          # DuckDB session database persistence
  ollama-models:     # Ollama model weights (shared between ollama and ollama-scorer)
  ollama-scorer-models:  # Separate volume for scorer Ollama instance
```

### 9.8 Claude Desktop Configuration

```json
{
  "mcpServers": {
    "pyrit": {
      "command": "docker",
      "args": [
        "run", "--rm", "-i",
        "--env-file", "/absolute/path/to/.env",
        "-v", "pyrit-db:/data",
        "-v", "/absolute/path/to/datasets:/datasets",
        "ghcr.io/your-username/pyrit-mcp:latest"
      ]
    }
  }
}
```

**Flag requirements:**
- `--rm` — container is removed after the session ends; no orphan containers accumulate
- `-i` — stdin stays open for MCP stdio transport; required for communication
- `--env-file` — injects secrets without embedding them in the command or shell history
- No `-t` flag — MCP stdio protocol breaks when a pseudo-TTY is allocated

### 9.9 Ollama Performance Tuning by Tier

| ENV Var | Tier 1 | Tier 3 | Tier 5 | Tier 7 |
|---|---|---|---|---|
| `OLLAMA_NUM_PARALLEL` | 1 | 2 | 4 | 8 |
| `OLLAMA_MAX_LOADED_MODELS` | 1 | 2 | 2 | 4 |
| `OLLAMA_FLASH_ATTENTION` | false | true | true | true |
| `OLLAMA_KV_CACHE_TYPE` | q8_0 | f16 | f16 | f16 |
| `OLLAMA_NUM_THREADS` | 4 | 16 | 32 | 64 |
| `OLLAMA_RUNNER_NUMCTX` | 2048 | 8192 | 16384 | 32768 |

---

## 10. GitHub Repository Architecture

### 10.1 Repository Details

- **Visibility:** Public
- **Registry:** `ghcr.io/<username>/pyrit-mcp`
- **Default branch:** `main`
- **Integration branch:** `develop`
- **Feature branches:** `feature/<name>`, `fix/<name>`

### 10.2 Branch Protection Rules on `main`

- Require pull request with at least 1 review before merge
- Require all CI status checks to pass
- No direct push permitted (including from maintainers)
- Require linear history (no merge commits from branches)

### 10.3 GitHub Actions Workflows

#### `ci.yml` — Every PR and push to `develop`

```yaml
Jobs:
  lint:
    - ruff check pyrit_mcp/ tests/
    - ruff format --check pyrit_mcp/ tests/
  typecheck:
    - mypy pyrit_mcp/
  test:
    strategy:
      matrix:
        python-version: ["3.10", "3.11", "3.12"]
    steps:
      - pytest tests/ --cov=pyrit_mcp
  docker-build-check:
    - docker build -f docker/Dockerfile . (no push, validates build only)
```

#### `build-and-push.yml` — Merge to `main`

```yaml
Jobs:
  build-and-push:
    - docker buildx build --platform linux/amd64,linux/arm64
    - Push to ghcr.io
    - Tag as :latest and :sha-<short-commit>
    - Publish :dev tag if branch is develop
```

Multi-platform build is required. Mac users on Apple Silicon (arm64) need a native image to avoid emulation overhead.

#### `release.yml` — Tag push matching `v*.*.*`

```yaml
Jobs:
  release:
    - Build and push :v1.2.3 and :latest tags
    - Create GitHub Release
    - Extract and attach CHANGELOG.md section for this version
```

### 10.4 Container Image Tag Strategy

| Tag | Published When | Purpose |
|---|---|---|
| `:latest` | Every merge to main | Always current stable version |
| `:sha-abc1234` | Every merge to main | Pinned reproducible deployments |
| `:v1.2.3` | On version tag push | Production pinning |
| `:dev` | Every push to develop | Pre-release testing |

### 10.5 `.gitignore` Additions

```
# Secrets
.env
.env.docker
.env.detected

# Database
*.db
*.duckdb
/data/

# Large model files
/models/
*.gguf

# Python
__pycache__/
.mypy_cache/
.ruff_cache/
dist/
*.egg-info/
.pytest_cache/
```

### 10.6 `.dockerignore`

```
.git/
.github/
tests/
evaluations/
*.md
.env*
__pycache__/
.mypy_cache/
models/
data/
docker-compose*.yml
Makefile
scripts/
config/
```

### 10.7 Pre-commit Hook Configuration

| Hook | Purpose |
|---|---|
| `ruff` | Python lint and format |
| `mypy` | Python type checking |
| `detect-secrets` | Prevent accidental credential commits (critical for a security project) |
| `hadolint` | Dockerfile best-practice linting |
| `end-of-file-fixer` | Ensure newline at end of every file |
| `trailing-whitespace` | Remove trailing whitespace |
| `check-yaml` | Validate all YAML files |
| `check-json` | Validate all JSON files |
| `check-added-large-files` | Block commits of files over 1MB |

---

## 11. System Detection & Model Recommendation

### 11.1 Three-Layer Detection Architecture

```
Layer 1: scripts/detect_system.sh
  Runs on host machine before Docker starts
  Reads:
    /proc/meminfo                    -> total and available RAM
    /proc/cpuinfo                    -> core count, CPU model
    lscpu                            -> socket count, NUMA topology
    numactl --hardware               -> detailed NUMA node layout
    nvidia-smi                       -> NVIDIA GPU model and VRAM
    rocm-smi                         -> AMD GPU model and VRAM
    which nvidia-container-toolkit   -> Docker GPU support availability
    docker info                      -> nvidia runtime availability
    /sys/kernel/mm/transparent_hugepage/enabled -> THP mode
    /sys/devices/system/cpu/*/cpufreq/scaling_governor -> CPU governor
    ulimit -l                        -> mlock limit
  Writes: .env.detected

Layer 2: docker/entrypoint.sh
  Runs inside container at startup
  Validates ENV vars match container-accessible resources
  Warns if OLLAMA_MEMORY_LIMIT is set too high for detected RAM
  Logs active configuration summary before launching server

Layer 3: pyrit_recommend_models MCP tool
  Runs at session start via Claude
  Reads config populated by Layer 1
  Returns ranked model recommendations as structured JSON
  Claude can immediately act on recommendations
```

### 11.2 Sample `.env.detected` Output (768GB Machine)

```bash
# Auto-generated by: make detect
# Timestamp: 2024-01-01T00:00:00Z
# DO NOT EDIT — re-run 'make detect' to refresh

# Hardware Detection
DETECTED_TOTAL_RAM_GB=768
DETECTED_AVAILABLE_RAM_GB=752
DETECTED_CPU_CORES=128
DETECTED_CPU_MODEL="AMD EPYC 9654 96-Core Processor"
DETECTED_CPU_SOCKETS=2
DETECTED_NUMA_NODES=2
DETECTED_HAS_NVIDIA_GPU=false
DETECTED_HAS_AMD_GPU=false
DETECTED_GPU_VRAM_GB=0
DETECTED_NVIDIA_TOOLKIT=false
DETECTED_INFERENCE_MODE=cpu
DETECTED_MLOCK_AVAILABLE=true
DETECTED_THP_MODE=madvise
DETECTED_CPU_GOVERNOR=performance

# Recommendations (written by make recommend)
RECOMMENDED_ATTACKER_BACKEND=llamacpp
RECOMMENDED_ATTACKER_MODEL=llama3.1:405b
RECOMMENDED_ATTACKER_QUANTIZATION=Q8_0
RECOMMENDED_ATTACKER_MODEL_FILE=llama3.1-405b-Q8_0.gguf
RECOMMENDED_ATTACKER_RAM_GB=400
RECOMMENDED_ATTACKER_THREADS=64
RECOMMENDED_ATTACKER_NUMA=distribute
RECOMMENDED_SCORER_BACKEND=ollama
RECOMMENDED_SCORER_MODEL=llama3.1:70b
RECOMMENDED_SCORER_QUANTIZATION=Q6_K
RECOMMENDED_SCORER_RAM_GB=48
RECOMMENDED_TOTAL_RAM_REQUIRED_GB=448
RECOMMENDED_REMAINING_RAM_GB=304
RECOMMENDED_COMPOSE_PROFILE=full-llamacpp
RECOMMENDED_OLLAMA_NUM_THREADS=32
RECOMMENDED_LLAMACPP_N_THREADS=64
RECOMMENDED_LLAMACPP_NUMA=distribute
RECOMMENDED_LLAMACPP_MLOCK=true
RECOMMENDED_LLAMACPP_CTX_SIZE=32768
```

### 11.3 Recommendation Decision Logic (`scripts/recommend_models.sh`)

```
INPUT: DETECTED_AVAILABLE_RAM_GB, DETECTED_INFERENCE_MODE, DETECTED_GPU_VRAM_GB

< 12GB available:
  attacker: dolphin-mistral Q4_K_M (~4GB) via ollama
  scorer:   substring scorer (no LLM)
  profile:  local-llm

12-31GB available:
  attacker: dolphin-mixtral:8x7b Q4_K_M (~26GB) via ollama
  scorer:   substring or toxic-bert classifier sidecar
  profile:  local-llm

32-63GB available:
  attacker: dolphin-mixtral:8x22b Q4_K_M (~48GB) via ollama
  scorer:   nous-hermes2 Q4_K_M (~7GB) via second ollama instance
  profile:  dual-ollama

64-127GB available:
  if ram >= 100:
    attacker: llama3.1:405b Q2_K (~100GB) via ollama
    note: warn about Q2 quality tradeoff
  else:
    attacker: dolphin-mixtral:8x22b Q6_K (~58GB) via ollama
  scorer:   llama3.1:70b Q4_K_M (~40GB) via second ollama instance
  profile:  dual-ollama

128-255GB available:
  attacker: llama3.1:405b Q4_K_M (~220GB) via llamacpp or ollama
  scorer:   llama3.1:70b Q8_0 (~70GB) via ollama
  profile:  full-llamacpp

256-511GB available:
  attacker: llama3.1:405b Q5_K_M (~265GB) via llamacpp direct
  scorer:   llama3.1:70b Q8_0 (~70GB) via ollama
  profile:  full-llamacpp

512GB+ available:
  attacker: llama3.1:405b Q8_0 (~400GB) via llamacpp direct
  scorer:   llama3.1:70b FP16 (~140GB) via ollama
  profile:  full-llamacpp
  note:     log remaining RAM headroom for optional third model

GPU OVERRIDE LOGIC:
  if DETECTED_HAS_NVIDIA_GPU and DETECTED_GPU_VRAM_GB > 0:
    calculate max layers that fit in VRAM
    set LLAMACPP_N_GPU_LAYERS or OLLAMA_GPU_LAYERS accordingly
    mixed CPU+GPU inference handled natively by both backends
```

### 11.4 `config/model_catalog.json` Schema

```json
{
  "models": [
    {
      "id": "llama3.1-405b",
      "family": "llama3",
      "params_b": 405,
      "uncensored": false,
      "ollama_name": "llama3.1:405b",
      "hf_repo": "meta-llama/Meta-Llama-3.1-405B-Instruct-GGUF",
      "recommended_role": "attacker",
      "min_ram_gb": 64,
      "optimal_ram_gb": 400,
      "notes": "Best open-weight model; practically uncensored at Q5+ quantizations",
      "quantizations": [
        {
          "quant_id": "Q8_0",
          "ram_gb": 400,
          "quality_score": 9,
          "gguf_filename": "Meta-Llama-3.1-405B-Instruct-Q8_0.gguf"
        },
        {
          "quant_id": "Q5_K_M",
          "ram_gb": 265,
          "quality_score": 8,
          "gguf_filename": "Meta-Llama-3.1-405B-Instruct-Q5_K_M.gguf"
        },
        {
          "quant_id": "Q4_K_M",
          "ram_gb": 220,
          "quality_score": 7,
          "gguf_filename": "Meta-Llama-3.1-405B-Instruct-Q4_K_M.gguf"
        },
        {
          "quant_id": "Q2_K",
          "ram_gb": 100,
          "quality_score": 5,
          "gguf_filename": "Meta-Llama-3.1-405B-Instruct-Q2_K.gguf"
        }
      ]
    }
  ]
}
```

### 11.5 `config/tier_profiles.json` Schema

Maps RAM ranges to complete recommended configurations. Read by both `recommend_models.sh` and `utils/system_detect.py` to keep recommendation logic consistent between shell and Python layers.

---

## 12. Configuration Architecture

### 12.1 `config.py` Design

Responsibilities:
- Load `.env.detected` first (lower priority baseline)
- Load `.env` second (higher priority, user overrides)
- Expose `ServerConfig` dataclass
- Expose `AttackerBackendConfig` dataclass
- Expose `ScorerBackendConfig` dataclass
- Expose `BackendType` enum
- Validate all required ENV vars on startup — fail fast with descriptive error

### 12.2 `BackendType` Enum Values

```python
class BackendType(Enum):
    OLLAMA = "ollama"
    LLAMACPP = "llamacpp"
    AZURE = "azure"
    OPENAI = "openai"
    GROQ = "groq"
    LMSTUDIO = "lmstudio"
    SUBSTRING = "substring"
    CLASSIFIER = "classifier"
```

### 12.3 `AttackerBackendConfig` Fields

| Field | Type | Default | Description |
|---|---|---|---|
| `backend_type` | BackendType | required | Which backend provider |
| `base_url` | str | required | Endpoint URL |
| `model` | str | required | Model identifier string |
| `api_key_env` | str | `""` | Env var name holding API key (blank for Ollama) |
| `temperature` | float | `1.0` | Higher = more creative attack generation |
| `max_tokens` | int | `2048` | Max tokens per generation |
| `timeout_seconds` | int | `60` | Request timeout |
| `quantization` | str | `""` | Active quantization for logging |

### 12.4 `ScorerBackendConfig` Fields

| Field | Type | Default | Description |
|---|---|---|---|
| `backend_type` | BackendType | required | Which backend provider |
| `base_url` | str | required | Endpoint URL |
| `model` | str | required | Model identifier string |
| `api_key_env` | str | `""` | Env var name holding API key |
| `temperature` | float | `0.0` | Zero for deterministic scoring |
| `scoring_scale` | str | `"likert_1_10"` | `likert_1_10`, `binary`, or `categorical` |
| `quantization` | str | `""` | Active quantization for logging |

### 12.5 Complete `.env.example`

```bash
# =============================================================================
# PyRIT MCP Server — Environment Configuration
# Copy to .env and fill in your values
# NEVER commit .env to git — it is in .gitignore
# =============================================================================

# ── Server ───────────────────────────────────────────────────────────────────
PYRIT_DB_PATH=/data/pyrit.db
PYRIT_LOG_LEVEL=INFO
PYRIT_DEFAULT_RPS=2               # default requests per second for attacks
PYRIT_DEFAULT_MAX_REQUESTS=100    # default max requests per attack campaign
PYRIT_SANDBOX_MODE=false          # true = log prompts but do not send requests

# ── Attacker LLM Backend ─────────────────────────────────────────────────────
# Options: ollama | llamacpp | azure | openai | groq | lmstudio
ATTACKER_BACKEND=ollama
ATTACKER_BASE_URL=http://ollama:11434    # change for non-Ollama backends
ATTACKER_MODEL=dolphin-mistral           # model identifier
ATTACKER_API_KEY_ENV=                    # name of env var with API key; blank for Ollama
ATTACKER_TEMPERATURE=1.0
ATTACKER_MAX_TOKENS=2048
ATTACKER_TIMEOUT=60
ATTACKER_QUANTIZATION=Q4_K_M             # informational only, for logging

# ── Scorer LLM Backend ───────────────────────────────────────────────────────
# Options: openai | azure | ollama | llamacpp | substring | classifier
SCORER_BACKEND=openai
SCORER_BASE_URL=https://api.openai.com/v1
SCORER_MODEL=gpt-4o
SCORER_API_KEY_ENV=SCORER_OPENAI_API_KEY
SCORER_TEMPERATURE=0.0
SCORER_QUANTIZATION=

# ── API Keys (referenced by _ENV vars above) ─────────────────────────────────
SCORER_OPENAI_API_KEY=sk-...

# ── Azure OpenAI (if ATTACKER_BACKEND=azure or SCORER_BACKEND=azure) ─────────
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com
AZURE_OPENAI_API_KEY=
AZURE_ATTACKER_DEPLOYMENT=
AZURE_SCORER_DEPLOYMENT=gpt-4o
AZURE_API_VERSION=2024-02-01
AZURE_CONTENT_FILTER_OVERRIDE=false   # requires Limited Access program enrollment

# ── Groq (if ATTACKER_BACKEND=groq or SCORER_BACKEND=groq) ───────────────────
GROQ_API_KEY=
GROQ_ATTACKER_MODEL=mixtral-8x7b-32768

# ── Ollama ────────────────────────────────────────────────────────────────────
OLLAMA_MODEL=dolphin-mistral            # attacker model pulled by ollama-init
OLLAMA_SCORER_MODEL=                    # scorer model (dual-ollama profile only)
OLLAMA_GPU_LAYERS=-1                    # -1=all layers on GPU, 0=CPU only
OLLAMA_NUM_PARALLEL=1
OLLAMA_MAX_LOADED_MODELS=1
OLLAMA_FLASH_ATTENTION=false
OLLAMA_KV_CACHE_TYPE=q8_0
OLLAMA_NUM_THREADS=4
OLLAMA_RUNNER_NUMCTX=2048

# ── llama.cpp Direct ─────────────────────────────────────────────────────────
LLAMACPP_MODEL_PATH=/models/llama3.1-405b-Q8_0.gguf
LLAMACPP_SCORER_MODEL_PATH=/models/llama3.1-70b-Q6_K.gguf
LLAMACPP_N_THREADS=64
LLAMACPP_CTX_SIZE=32768
LLAMACPP_BATCH_SIZE=512
LLAMACPP_N_PARALLEL=4
LLAMACPP_MLOCK=true
LLAMACPP_MMAP=true
LLAMACPP_NUMA=distribute               # use 'distribute' for dual-socket machines
LLAMACPP_N_GPU_LAYERS=0                # 0=CPU only
LLAMACPP_PORT=8080

# ── Per-Instance Quantization (dual-ollama / full-llamacpp profiles) ──────────
ATTACKER_MODEL_FILE=llama3.1-405b-Q8_0.gguf
ATTACKER_QUANT=Q8_0
ATTACKER_RAM_ALLOCATION_GB=400
ATTACKER_N_THREADS=64
ATTACKER_CTX_SIZE=32768
ATTACKER_MLOCK=true

SCORER_MODEL_FILE=llama3.1-70b-Q6_K.gguf
SCORER_QUANT=Q6_K
SCORER_RAM_ALLOCATION_GB=48
SCORER_N_THREADS=32
SCORER_CTX_SIZE=8192
SCORER_MLOCK=true

# ── Target Application Credentials ────────────────────────────────────────────
TARGET_BEARER_TOKEN=
TARGET_OPENAI_API_KEY=
TARGET_AZURE_API_KEY=
TARGET_AZURE_ENDPOINT=

# ── HuggingFace (for model downloads) ────────────────────────────────────────
HUGGINGFACE_TOKEN=                     # required for gated model downloads
```

---

## 13. Linux Bare Metal Optimizations

These optimizations apply to Linux bare metal deployments. They are detected by `detect_system.sh`, validated by `validate_env.sh`, and documented in a dedicated README section.

### 13.1 NUMA Topology (CRITICAL for dual-socket)

Detection: `numactl --hardware` identifies socket count and NUMA node layout

For dual-socket machines, `--numa distribute` is set automatically in the llama.cpp config. Without it, threads fetch model data across the inter-socket memory bus, which causes heavy latency. The performance impact is **2-3x throughput difference** on models too large to fit in a single NUMA node's memory.

### 13.2 Transparent Huge Pages

Detection: `cat /sys/kernel/mm/transparent_hugepage/enabled`

Recommended setting: `madvise` (not `always`, not `never`)

Command: `echo madvise > /sys/kernel/mm/transparent_hugepage/enabled`

For permanent persistence, document in README: add to `/etc/rc.local` or a systemd unit.

### 13.3 Memory Locking (mlock)

llama.cpp `--mlock` prevents large model files from being swapped to disk mid-inference. Required for large models on Tier 5+.

Detection: `ulimit -l` reports the mlock limit in KB. Unlimited is required.

Permanent configuration: add to `/etc/security/limits.conf`:
```
* soft memlock unlimited
* hard memlock unlimited
```

`validate_env.sh` checks this and prints a warning with fix instructions if mlock is restricted.

### 13.4 CPU Frequency Governor

Detection: `cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor`

Recommended: `performance` mode. `powersave` caps CPU frequency and significantly reduces inference throughput.

Command: `echo performance | tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor`

`detect_system.sh` reports the current governor. `validate_env.sh` warns if it is not `performance`.

### 13.5 Docker Memory Access on Linux Bare Metal

On bare metal Linux, Docker containers access all available system RAM by default. No `--memory` constraint is needed in compose files. This is a **Linux-only advantage** — Docker Desktop on Mac and Windows caps container memory access. This distinction is explicitly documented in the README Tier notes.

---

## 14. Makefile Specification

### 14.1 Complete Target List

| Target | Description |
|---|---|
| `make detect` | Detect system hardware; write `.env.detected` |
| `make recommend` | Read `.env.detected`; recommend models; write recommendations |
| `make setup` | Run detect + recommend + validate-env in sequence |
| `make download-model` | Interactive GGUF downloader (prompts for model and quant) |
| `make build` | `docker compose build` all services |
| `make up` | `docker compose up` using auto-detected profile from `.env.detected` |
| `make up-gpu` | `docker compose --profile local-llm-gpu up` |
| `make up-llamacpp` | `docker compose --profile full-llamacpp up` |
| `make up-full` | `docker compose --profile full up` |
| `make up-dev` | `docker compose -f docker-compose.dev.yml up` |
| `make down` | `docker compose down` |
| `make test` | `pytest tests/ --cov=pyrit_mcp` |
| `make lint` | `ruff check` and `ruff format --check` |
| `make typecheck` | `mypy pyrit_mcp/` |
| `make benchmark` | Run inference speed test on configured backend |
| `make validate-env` | Check all required env vars; check mlock/THP/governor |
| `make clean` | Remove containers and named volumes (preserves model files) |
| `make clean-models` | Remove downloaded GGUF files (prompts for confirmation) |
| `make logs` | `docker compose logs -f` |
| `make shell` | `docker exec -it` into running `pyrit-mcp` container |
| `make release` | Bump version, update CHANGELOG, create git tag, push |
| `make pull-latest` | Pull latest image from ghcr.io |

### 14.2 `make detect` Implementation Detail

Invokes `scripts/detect_system.sh` which:
1. Reads `/proc/meminfo` for total and available RAM in GB
2. Reads `/proc/cpuinfo` and `lscpu` for core count, socket count, CPU model
3. Runs `numactl --hardware` for detailed NUMA node topology
4. Checks `nvidia-smi` for NVIDIA GPU (model, VRAM, driver version)
5. Checks `rocm-smi` for AMD GPU (model, VRAM)
6. Checks `which nvidia-container-toolkit` for Docker GPU support
7. Checks `docker info` for nvidia runtime availability
8. Reads THP setting from sysfs
9. Reads CPU governor from sysfs
10. Runs `ulimit -l` for mlock limit
11. Writes all findings to `.env.detected`
12. Prints human-readable hardware summary to stdout

### 14.3 `make recommend` Implementation Detail

Invokes `scripts/recommend_models.sh` which:
1. Sources `.env.detected`
2. Reads `config/model_catalog.json` for model metadata
3. Reads `config/tier_profiles.json` for tier thresholds
4. Applies the decision tree logic documented in Section 11.3
5. Calculates total RAM allocation (attacker + scorer) and remaining headroom
6. Appends recommendations to `.env.detected`
7. Prints a recommendation summary with RAM allocation breakdown to stdout

---

## 15. Session & State Model

### 15.1 DuckDB Session Schema

```sql
-- Configured targets
CREATE TABLE targets (
    target_id UUID PRIMARY KEY,
    target_type VARCHAR NOT NULL,  -- http | openai | azure
    config_json JSON NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Loaded datasets
CREATE TABLE datasets (
    dataset_id UUID PRIMARY KEY,
    name VARCHAR NOT NULL UNIQUE,
    category VARCHAR,
    prompt_count INTEGER,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Configured scorers
CREATE TABLE scorers (
    scorer_id UUID PRIMARY KEY,
    scorer_type VARCHAR NOT NULL,  -- llm | substring | classifier
    config_json JSON NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Attack campaigns
CREATE TABLE attacks (
    attack_id UUID PRIMARY KEY,
    target_id UUID REFERENCES targets(target_id),
    dataset_name VARCHAR,
    orchestrator_type VARCHAR NOT NULL,
    status VARCHAR NOT NULL,  -- running | complete | cancelled | failed
    started_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP
);

-- Individual attack results
CREATE TABLE results (
    result_id UUID PRIMARY KEY,
    attack_id UUID REFERENCES attacks(attack_id),
    prompt_text TEXT NOT NULL,
    response_text TEXT,
    scores JSON,  -- {scorer_id: score_value, ...}
    timestamp TIMESTAMP DEFAULT NOW()
);
```

### 15.2 Session Persistence Behavior

Sessions persist across MCP server restarts via the DuckDB file at `$PYRIT_DB_PATH`. The Docker named volume `pyrit-db` ensures data survives container restarts and `docker compose down` cycles.

`pyrit_clear_session` with `confirm: true` drops and recreates all tables.

### 15.3 Sandbox Mode

When `PYRIT_SANDBOX_MODE=true`:
- All orchestrators record prompts to DuckDB as normal
- No actual HTTP requests are sent to target applications
- Responses are replaced with configurable mock data
- Attack lifecycle (running → complete) proceeds normally
- Enables testing the MCP server and its tool integration without a live target
- Also prevents accidentally running attacks on the wrong endpoint

This must be checked at the top of every orchestrator tool before any network activity.

---

## 16. Security Considerations

### 16.1 Credential Handling

- Tool parameters only accept the **name** of an env var containing a credential, never the credential value itself
- `.env` and `.env.detected` are in `.gitignore` — never committed
- `detect-secrets` pre-commit hook provides a second layer of protection
- `.env.example` contains only placeholder strings; never real keys
- All log output redacts API keys — use `***` or `[REDACTED]`

### 16.2 Prompt Injection Defense in the Server Itself

The server sends adversarial prompts and receives potentially adversarial responses. The server must not be injectable via those responses:

- Tool input validation via Pydantic rejects unexpected fields and types
- Target application responses are treated as data only — never executed or interpreted as instructions
- The server never re-evaluates content received from target application responses

### 16.3 Container Security

- Production image runs as non-root user `pyrit` (uid 1000)
- Minimum capability set — no `--privileged` flags
- GPU profile requires `nvidia` runtime but no `--privileged`
- AMD profile mounts only the required device files

### 16.4 Network Exposure

The MCP server is stdio-only and binds to no network ports. Ollama and llama.cpp sidecars bind to the internal Docker compose network only — not exposed on the host network interface.

### 16.5 Responsible Use Documentation

The README must include a prominent responsible use statement:
- This tool is for **authorized security testing only**
- Users must have explicit written permission to test the target application
- The project maintainers accept no liability for unauthorized or malicious use
- Users are responsible for compliance with applicable laws and regulations

---

## 17. Phased Build Plan

### Phase 0 — Repository Foundation ✅ COMPLETE

**Goal:** Public GitHub repository exists. CI is green. Developer can clone and run `make setup` to get hardware detection output.

**Deliverables:**

| Item | Description |
|---|---|
| GitHub repository | Public repo created with branch protection on `main` |
| `pyproject.toml` | Package metadata; ruff, mypy, pytest configuration sections |
| `requirements.txt` | Pinned production dependencies |
| `requirements-dev.txt` | Pinned dev dependencies |
| `.env.example` | All ENV vars documented with descriptions |
| `.gitignore` | Comprehensive ignores including models/, data/, .env files |
| `.dockerignore` | Excludes tests, docs, local configs from image |
| `.pre-commit-config.yaml` | All hooks configured and working |
| `Makefile` | All targets defined; most are functional stubs; detect + recommend working |
| `scripts/detect_system.sh` | Fully functional hardware detection |
| `scripts/recommend_models.sh` | Fully functional model recommendation engine |
| `config/model_catalog.json` | All models from Tier 1 through Tier 7 populated |
| `config/tier_profiles.json` | All tier thresholds and profile mappings populated |
| `README.md` | Project overview, quick start, tier selection guide |
| `CONTRIBUTING.md` | Dev setup, pre-commit, test instructions, PR process |
| `CHANGELOG.md` | Initialized with unreleased section |
| `LICENSE` | License selected and added |
| `.github/workflows/ci.yml` | Lint + typecheck + test matrix (Python 3.10/3.11/3.12) |
| `.github/ISSUE_TEMPLATE/` | Bug report and feature request templates |
| `pyrit_mcp/__init__.py` | Version string `__version__ = "0.1.0"` |
| Placeholder test files | All `tests/test_*.py` files with one passing placeholder test each |
| `models/.gitkeep` | Placeholder to track models directory |
| `data/.gitkeep` | Placeholder to track data directory |

**Exit criteria:**
- `make setup` runs on a developer machine and prints hardware detection output
- CI passes (green) on the empty project structure
- All pre-commit hooks pass on an empty commit

**Phase 0 status: ✅ Complete.** All deliverables shipped and CI green.

---

### Phase 1 — Core MCP Server, First Attack End-to-End ✅ COMPLETE

**Goal:** A real attack campaign runs end-to-end via Claude Desktop using Docker and Ollama.

**Deliverables:**

| Item | Description |
|---|---|
| `docker/Dockerfile` | Production image builds successfully |
| `docker/entrypoint.sh` | ENV validation + DB init + server launch |
| `docker-compose.yml` | Base service + `local-llm` profile with Ollama + `ollama-init` |
| `pyrit_mcp/server.py` | FastMCP server; tool registration for Phase 1 domains |
| `pyrit_mcp/config.py` | ServerConfig, AttackerBackendConfig, ScorerBackendConfig, BackendType |
| `pyrit_mcp/utils/db.py` | DuckDB singleton connection; schema initialization |
| `pyrit_mcp/utils/rate_limiter.py` | Token bucket rate limiter for API calls |
| `pyrit_mcp/utils/formatters.py` | Structured JSON output helpers |
| `pyrit_mcp/tools/targets.py` | All 6 target management tools |
| `pyrit_mcp/tools/orchestrators.py` | `pyrit_run_prompt_sending_orchestrator` with attack_id async pattern |
| `pyrit_mcp/tools/scorers.py` | `pyrit_configure_substring_scorer` + `pyrit_score_response` |
| `pyrit_mcp/tools/results.py` | All 8 results tools |
| `pyrit_mcp/tools/datasets.py` | `pyrit_list_builtin_datasets` + `pyrit_load_dataset` + `pyrit_preview_dataset` |
| `tests/conftest.py` | Shared fixtures; mock PyRIT backend |
| `tests/test_targets.py` | Target management tool tests |
| `tests/test_results.py` | Results tool tests |
| `Makefile` | `make build`, `make up`, `make down`, `make logs` all functional |
| Claude Desktop config | Ready-to-use snippet documented in README |

**Exit criteria:**
- Claude Desktop can: configure a target, load a dataset, start an attack, poll status, retrieve results
- Ollama is running `dolphin-mistral` as the attacker model
- Substring scorer correctly identifies mock jailbreaks in test data
- All Phase 1 tests pass

**Phase 1 status: ✅ Complete.** All deliverables shipped. 6 target tools, 3 orchestrator tools (prompt_sending + status + cancel), 3 scorer tools, 3 dataset tools, 8 results tools, DuckDB schema, rate limiter, formatters, Dockerfile, entrypoint.sh, docker-compose.yml (all 9 profiles), 36 tests across test_targets.py (16) and test_results.py (20). Four design decisions resolved (see Section 18).

---

### Phase 2 — All Orchestrators, All Scorers, GPU Profiles ✅ COMPLETE

**Goal:** Complete PyRIT orchestrator and scorer surface covered. GPU-accelerated profiles available.

**Deliverables:**

| Item | Description |
|---|---|
| `pyrit_mcp/tools/orchestrators.py` | All 8 orchestrators complete with async attack_id pattern |
| `pyrit_mcp/tools/scorers.py` | LLM scorer + classifier scorer added; cost guard implemented |
| `pyrit_mcp/tools/datasets.py` | All 7 dataset tools complete |
| `docker-compose.yml` | `local-llm-gpu` NVIDIA profile added |
| `docker-compose.yml` | `local-llm-amd` ROCm profile added |
| `docker/Dockerfile.scorer` | HuggingFace classifier sidecar image |
| `docker-compose.yml` | `local-scorer` profile added |
| `tests/test_orchestrators.py` | Tests for all 8 orchestrators |
| `tests/test_scorers.py` | Tests for all scorer types |
| `.github/workflows/build-and-push.yml` | Multi-platform build to ghcr.io on merge to main |
| `:dev` tag | Auto-published on every push to develop |

**Exit criteria:**
- All 6 orchestrator types run successfully against a mock target
- NVIDIA GPU profile activates GPU device and is documented in README
- Multi-platform image builds successfully on CI
- `:dev` tag is visible on ghcr.io after a push to develop

---

### Phase 3 — llama.cpp Direct, Per-Instance Quantization, Dual-Ollama ✅ COMPLETE

**Goal:** High-RAM tiers fully supported. Attacker and scorer on independent instances with separate quantization levels.

**Deliverables:**

| Item | Description |
|---|---|
| `docker-compose.yml` | `full-llamacpp` profile: llama.cpp attacker + Ollama scorer |
| `docker-compose.yml` | `dual-ollama` profile: two independent Ollama instances |
| `scripts/download_model.sh` | HuggingFace GGUF downloader with disk space check and confirmation |
| `scripts/benchmark.sh` | Inference tokens-per-second tester for configured backend |
| `pyrit_mcp/utils/system_detect.py` | Python module wrapping `.env.detected` for in-process access |
| `pyrit_mcp/tools/backends.py` | All 9 backend management tools including `pyrit_recommend_models` |
| `tests/test_backends.py` | Backend management tool tests |
| `tests/test_system_detect.py` | System detect utility tests |
| `scripts/validate_env.sh` | Pre-flight check: mlock limit, THP mode, CPU governor, NUMA |
| `Makefile` | `make download-model`, `make up-llamacpp`, `make benchmark` functional |
| README | Per-tier setup guide sections; NUMA/THP/mlock documentation |

**Exit criteria:**
- `docker compose --profile full-llamacpp up` successfully runs attacker and scorer on separate instances
- `make recommend` outputs correct configuration for the host machine's detected hardware
- `pyrit_recommend_models` MCP tool returns correct recommendations that match `make recommend` output
- Verified functioning on Tier 7 (768GB) machine with `llama3.1:405b Q8_0` as attacker

---

### Phase 4 — Converters, Sandbox Mode, Report Generation ✅ COMPLETE

**Goal:** Full converter chain. Sandbox mode enables safe testing. Report generation pipeline complete.

**Deliverables:**

| Item | Description |
|---|---|
| `pyrit_mcp/tools/converters.py` | All 11 converters with list, apply, and chain tools |
| `tests/test_converters.py` | Converter tool tests |
| Sandbox mode | `PYRIT_SANDBOX_MODE=true` implemented in all orchestrators |
| `pyrit_generate_report` | Returns complete structured JSON; validated by tests |
| `pyrit_compare_attacks` | Diff results between two attack runs |
| `pyrit_estimate_attack_cost` | Token count and cost estimation before LLM scorer runs |
| `docker/Dockerfile.dev` | Dev image with hot reload |
| `docker-compose.dev.yml` | Dev compose override with volume mounts |
| `Makefile` | `make up-dev`, `make shell` functional |

**Exit criteria:**
- `PYRIT_SANDBOX_MODE=true` runs a complete Crescendo campaign with zero real network requests
- `pyrit_generate_report` returns structured JSON that Claude correctly narrates into a vulnerability report
- Converter chain applies multiple transforms to a dataset and returns modified prompts
- Dev image hot-reloads Python changes without rebuild

---

### Phase 5 — Evaluation Suite, Documentation, v1.0.0 Release

**Goal:** Production-ready release with comprehensive documentation and evaluation suite.

**Deliverables:**

| Item | Description |
|---|---|
| `evaluations/eval_questions.xml` | 10 QA pairs covering all tool domains |
| `README.md` | Complete: overview, quick start, all tier guides, Claude Desktop config, Docker profiles, NUMA/THP/mlock setup, model download guide, responsible use statement |
| `CONTRIBUTING.md` | Complete: dev setup, pre-commit, testing, PR process, release process |
| `CHANGELOG.md` | Complete history through v1.0.0 |
| `.github/workflows/release.yml` | Tag-triggered versioned release workflow |
| `Makefile` | `make release` functional |
| All tests | Full test suite with 80%+ coverage |
| mypy | Zero errors across entire codebase |
| ruff | Zero warnings across entire codebase |
| `v1.0.0` git tag | Triggers build-and-push; publishes `:v1.0.0` and `:latest` to ghcr.io |

**Exit criteria:**
- `v1.0.0` tag triggers successful release workflow
- `ghcr.io/<username>/pyrit-mcp:v1.0.0` and `:latest` are publicly pullable
- All CI checks are green on main
- Claude Desktop config documented and manually tested

---

## 18. Open Design Decisions

These decisions are documented for resolution during Phase 0 or Phase 1. When resolved during implementation, update this section and add a note to CHANGELOG.md.

| Decision | Options | Notes |
|---|---|---|
| PyRIT abstraction level | Wrap `PromptRequestPiece` directly vs. higher-level abstraction | **✅ Resolved (Phase 1):** Thin HTTP wrapper over PyRIT targets. Simpler, more flexible for Phase 1 scope. |
| Crescendo multi-turn state | DuckDB persistence vs. in-process memory | **✅ Resolved (Phase 1):** DuckDB persistence. Restartability wins. |
| Multi-turn state serialization | JSON blob in DuckDB vs. normalized relational tables | JSON blob simpler to implement; normalized more queryable |
| `pyrit_generate_report` scope | Return raw JSON only vs. call internal LLM | **✅ Resolved (Phase 1):** Raw JSON only. Avoids circular LLM dependencies; report narration stays in Claude's context window. |
| HuggingFace authentication | HF token in `.env` for automation vs. manual download only | HF token in `.env` preferred for scripted workflows |
| llama.cpp source vs. official image | Build from source vs. `ghcr.io/ggerganov/llama.cpp:server` | **✅ Resolved (Phase 1):** Official `ghcr.io/ggerganov/llama.cpp:server` image. Less maintenance burden. |
| Ollama version pinning | `:latest` vs. specific version tag | Pin to specific version for reproducibility |
| Test coverage target | 70%, 80%, 90% | 80% recommended as practical minimum |
| GitHub username | Personal account vs. new organization | Clarify before Phase 0 |
| License | MIT, Apache 2.0, or other | Clarify before Phase 0; MIT or Apache 2.0 recommended for open source |

---

## 19. Coding Instructions for Claude

This section is addressed directly to the Claude Sonnet 4.6 instance executing this project.

### 19.1 Where to Start

Begin with **Phase 0**. Do not write any application code (tools, server, config, utils) until the repository foundation is complete and CI is green on an empty project. The foundation infrastructure catches errors early and is itself a deliverable.

### 19.2 Implementation Order Within Each Phase

For every Phase, implement in this exact order:

1. **Write failing tests** that define the expected behavior for this phase
2. **Implement the code** to make the tests pass
3. **Add type annotations** — `mypy` must pass with zero errors
4. **Write docstrings** on every public function, class, and module
5. **Update CHANGELOG.md** with a summary of changes under the Unreleased section

### 19.3 Tool Implementation Template

Every tool must follow this exact pattern:

```python
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field
from typing import Any

class PyritToolNameInput(BaseModel):
    """Input schema for pyrit_tool_name."""
    param_one: str = Field(
        description="Clear description of this parameter and valid values"
    )
    param_two: int = Field(
        default=10,
        description="Optional parameter with default; explain what the default means"
    )

@mcp.tool(
    description="Concise one-line description. When to use this tool. What it returns.",
    annotations={
        "readOnlyHint": True,        # True if no state is modified
        "destructiveHint": False,    # True if data can be deleted or irreversibly changed
        "idempotentHint": False,     # True if calling multiple times has same effect as once
    }
)
async def pyrit_tool_name(params: PyritToolNameInput) -> dict[str, Any]:
    """
    Extended docstring explaining the full behavior, side effects, and return schema.

    Returns:
        dict with keys: status ("success" or "error"), data (on success),
        error (on failure), suggestion (on failure)
    """
    try:
        result = await _do_the_thing(params)
        return {
            "status": "success",
            "data": result
        }
    except SpecificPyritError as e:
        return {
            "status": "error",
            "error": str(e),
            "suggestion": "Call pyrit_list_targets to see configured targets, then retry."
        }
    except Exception as e:
        return {
            "status": "error",
            "error": f"Unexpected error: {e}",
            "suggestion": "Check PYRIT_LOG_LEVEL=DEBUG for full stack trace."
        }
```

### 19.4 Universal Implementation Rules

**These rules apply to every tool in every domain without exception:**

- All tool return values are structured JSON dicts — never plain strings, never prose
- All I/O operations (database, HTTP, file) are async/await — no synchronous blocking
- Error messages always include a `suggestion` field with the next actionable step
- Every orchestrator tool returns an `attack_id` string immediately and runs async — never block
- Destructive tools check for `confirm: bool = False` parameter; return an error if False
- Credentials are only accepted as env var names; the actual key value is read server-side
- API keys are never logged — redact with `[REDACTED]` in any log output
- `PYRIT_SANDBOX_MODE` is checked at the top of every orchestrator before any network call

### 19.5 Config Loading Pattern

```python
# pyrit_mcp/config.py
from dataclasses import dataclass, field
from enum import Enum
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env.detected first (lower priority — auto-detected values)
detected_env = Path(".env.detected")
if detected_env.exists():
    load_dotenv(detected_env, override=False)

# Load .env second (higher priority — user overrides)
load_dotenv(override=True)


class BackendType(Enum):
    OLLAMA = "ollama"
    LLAMACPP = "llamacpp"
    AZURE = "azure"
    OPENAI = "openai"
    GROQ = "groq"
    LMSTUDIO = "lmstudio"
    SUBSTRING = "substring"
    CLASSIFIER = "classifier"


@dataclass
class AttackerBackendConfig:
    backend_type: BackendType
    base_url: str
    model: str
    temperature: float = 1.0
    max_tokens: int = 2048
    timeout_seconds: int = 60
    quantization: str = ""
    api_key_env: str = ""

    @property
    def api_key(self) -> str:
        """Read the actual API key from the environment at call time."""
        if not self.api_key_env:
            return ""
        return os.environ.get(self.api_key_env, "")


@dataclass
class ScorerBackendConfig:
    backend_type: BackendType
    base_url: str
    model: str
    temperature: float = 0.0
    scoring_scale: str = "likert_1_10"
    quantization: str = ""
    api_key_env: str = ""

    @property
    def api_key(self) -> str:
        if not self.api_key_env:
            return ""
        return os.environ.get(self.api_key_env, "")


@dataclass
class ServerConfig:
    db_path: str = field(default_factory=lambda: os.environ.get("PYRIT_DB_PATH", "/data/pyrit.db"))
    log_level: str = field(default_factory=lambda: os.environ.get("PYRIT_LOG_LEVEL", "INFO"))
    default_rps: float = field(default_factory=lambda: float(os.environ.get("PYRIT_DEFAULT_RPS", "2")))
    default_max_requests: int = field(default_factory=lambda: int(os.environ.get("PYRIT_DEFAULT_MAX_REQUESTS", "100")))
    sandbox_mode: bool = field(default_factory=lambda: os.environ.get("PYRIT_SANDBOX_MODE", "false").lower() == "true")
```

### 19.6 DuckDB Singleton Pattern

```python
# pyrit_mcp/utils/db.py
import duckdb
import os
from pathlib import Path

_connection: duckdb.DuckDBPyConnection | None = None


def get_connection() -> duckdb.DuckDBPyConnection:
    """Return the singleton DuckDB connection, creating it if necessary."""
    global _connection
    if _connection is None:
        db_path = Path(os.environ.get("PYRIT_DB_PATH", "/data/pyrit.db"))
        db_path.parent.mkdir(parents=True, exist_ok=True)
        _connection = duckdb.connect(str(db_path))
        _initialize_schema(_connection)
    return _connection


def _initialize_schema(conn: duckdb.DuckDBPyConnection) -> None:
    """Create tables if they do not exist."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS targets (
            target_id UUID PRIMARY KEY,
            target_type VARCHAR NOT NULL,
            config_json JSON NOT NULL,
            created_at TIMESTAMP DEFAULT NOW()
        )
    """)
    # ... additional tables as per Section 15.1
```

### 19.7 Async Attack Pattern

```python
# pyrit_mcp/tools/orchestrators.py
import asyncio
import uuid
from typing import Any

# In-process registry of running attack tasks
_running_attacks: dict[str, asyncio.Task[None]] = {}


async def pyrit_run_prompt_sending_orchestrator(
    params: PromptSendingInput
) -> dict[str, Any]:
    """Launch an attack campaign asynchronously and return attack_id immediately."""
    if os.environ.get("PYRIT_SANDBOX_MODE", "false").lower() == "true":
        return await _run_sandbox_attack(params)

    attack_id = str(uuid.uuid4())
    task = asyncio.create_task(
        _run_attack_background(attack_id, params),
        name=f"attack-{attack_id}"
    )
    _running_attacks[attack_id] = task

    return {
        "status": "started",
        "attack_id": attack_id,
        "message": (
            f"Attack campaign started successfully. "
            f"Poll progress with: pyrit_get_attack_status(attack_id='{attack_id}')"
        )
    }


async def _run_attack_background(attack_id: str, params: Any) -> None:
    """Background task: run the PyRIT orchestrator and update DuckDB on completion."""
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE attacks SET status='running' WHERE attack_id=?",
            [attack_id]
        )
        # ... run PyRIT orchestrator
        conn.execute(
            "UPDATE attacks SET status='complete', completed_at=NOW() WHERE attack_id=?",
            [attack_id]
        )
    except Exception as e:
        conn.execute(
            "UPDATE attacks SET status='failed', completed_at=NOW() WHERE attack_id=?",
            [attack_id]
        )
        raise
    finally:
        _running_attacks.pop(attack_id, None)
```

### 19.8 Docker Layer Order Rule

When modifying `docker/Dockerfile`, maintain this layer order strictly to preserve build cache:

```dockerfile
# Layer 1: OS system dependencies (changes rarely — cache friendly)
RUN apt-get update && apt-get install -y gcc libgomp1 && rm -rf /var/lib/apt/lists/*

# Layer 2: Python dependencies (changes occasionally — cache on requirements.txt hash)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Layer 3: PyRIT (large, changes rarely — separate layer)
RUN pip install --no-cache-dir pyrit

# Layer 4: Application code (changes frequently — last layer)
COPY pyrit_mcp/ ./pyrit_mcp/

# Layer 5: Entrypoint
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]
```

### 19.9 Module and Naming Conventions

- All tool functions follow the `pyrit_<verb>_<noun>` naming pattern without exception
- Private helper functions are prefixed with underscore: `_<verb>_<noun>`
- All tool modules in `pyrit_mcp/tools/` export their tools via `tools/__init__.py`
- `server.py` imports all tools from `tools/__init__.py` only — never directly from tool modules
- `tools/__init__.py` is the single registration point, imported by `server.py`

### 19.10 Resolving Open Decisions During Implementation

When a decision from Section 18 is reached during implementation:

1. Make the decision and document the rationale in a code comment at the decision site
2. Add a note to CHANGELOG.md under the current phase heading
3. Update Section 18 of this document to mark the decision as Resolved with the chosen option
4. If the decision has broad architectural impact, update the relevant section of this document

---

*End of PyRIT MCP Server Comprehensive Project Plan*

*Document Version 1.0.0 — Planning Complete — Ready for Implementation*
