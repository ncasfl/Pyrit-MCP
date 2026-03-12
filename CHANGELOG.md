# Changelog

All notable changes to pyrit-mcp are documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versioning follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Added (Phase 5 — Evaluation Suite, Coverage, v1.0.0 Readiness)

**Evaluation suite:**
- `evaluations/eval_questions.xml` — 10 QA pairs covering all tool domains for automated evaluation

**Test coverage boost (65% → 82%):**
- `tests/test_datasets.py` — 46 tests covering all 7 dataset tools (was 11% coverage, now 94%)
- `tests/test_targets.py` — 55 tests covering all 6 target tools plus probe helpers (now 100%)
- `tests/test_init.py` — 2 tests verifying `register_all_tools` registers all exported tools (now 100%)
- Total test count: 253 (up from 170)

**Configuration:**
- `pyproject.toml` — Coverage `fail_under` raised from 60% to 80%

**Code quality:**
- mypy strict: zero errors across all 17 source files
- ruff lint + format: zero warnings across all source and test files

---

### Added (Phase 4 — Converters, Sandbox Mode, Report Generation)

**Domain 6 — Converters (3 tools, 12 built-in converters):**
- `pyrit_list_converters` — List all available prompt converters with descriptions
- `pyrit_apply_converter` — Apply a single converter to transform a prompt string
- `pyrit_chain_converters` — Apply a sequence of converters in order with intermediate steps
- Built-in converters: `base64`, `rot13`, `leetspeak`, `unicode_substitution`, `morse_code`,
  `caesar_cipher`, `language_translation`, `tone_academic`, `tone_fictional`,
  `suffix_injection`, `prefix_injection`, `character_space_insertion`

**Already complete from prior phases (verified):**
- Sandbox mode: `PYRIT_SANDBOX_MODE=true` implemented in all 6 orchestrators (Phase 1/2)
- `pyrit_generate_report` — returns structured JSON for Claude narration (Phase 1)
- `pyrit_compare_attacks` — diffs two attack campaigns by jailbreak rate (Phase 1)
- `pyrit_estimate_attack_cost` — token count and cost estimation (Phase 3)
- `docker/Dockerfile.dev` — dev image with hot reload, debugpy, sandbox mode default (Phase 0)
- `docker-compose.dev.yml` — dev compose with bind-mounts and debug port (Phase 0)
- `Makefile` — `make up-dev`, `make shell` functional (Phase 0)

**Test suite:**
- `tests/test_converters.py` — 14 tests covering all 3 converter tools and 12 converters

**Code quality:**
- mypy strict: zero errors on Phase 4 source files
- ruff lint + format: zero warnings

---

### Added (Phase 3 — Backend Management, Hardware Detection, Model Recommendation)

**Domain 7 — Backend Management (9 tools):**
- `pyrit_configure_attacker_backend` — Switch attacker LLM backend at runtime (Ollama, OpenAI, Azure, llama.cpp)
- `pyrit_configure_scorer_backend` — Switch scorer LLM backend at runtime; substring/classifier bypass base_url validation
- `pyrit_list_backend_options` — Show current attacker/scorer config and all available backend types
- `pyrit_test_backend_connectivity` — HTTP probe with latency measurement for attacker or scorer backend
- `pyrit_estimate_attack_cost` — Token usage and cost estimation from loaded dataset and backend type
- `pyrit_recommend_models` — RAM-tiered model recommendations using `tier_profiles.json` and `model_catalog.json`
- `pyrit_pull_ollama_model` — Pull model into Ollama with confirmation guard (`confirm_size_gb=True`)
- `pyrit_list_ollama_models` — List all models available in local Ollama instance
- `pyrit_benchmark_backend` — Inference speed test (tokens/sec) on configured backend

**Utilities:**
- `pyrit_mcp/utils/system_detect.py` — Hardware detection parser (`.env.detected`), tier matching,
  model enrichment from catalog; public API: `get_system_profile()`, `recommend_models()`,
  `load_tier_profiles()`, `load_model_catalog()`

**Tool registration:**
- `pyrit_mcp/tools/__init__.py` — All 9 backend tools registered with descriptions and `ToolAnnotations`;
  `_ann()` simplified to direct `ToolAnnotations` (removed try/except guard); imports sorted by ruff

**Test suite:**
- `tests/test_backends.py` — 23 tests covering all 9 backend tools; httpx async context manager mocks
- `tests/test_system_detect.py` — 16 tests covering `get_system_profile`, `recommend_models`, loaders
- `tests/test_targets.py` — Fixed `mocker` fixture dependency (replaced with `unittest.mock.patch`)

**Code quality:**
- mypy strict: zero errors across all Phase 3 source files
- ruff lint + format: zero warnings; imports and `__all__` sorted

---

### Added (Phase 2 — All Orchestrators, All Scorers, GPU Profiles)

**Circular import fix — new shared utility:**
- `pyrit_mcp/utils/scoring.py` — `substring_score()` extracted as single source of truth;
  eliminates runtime cross-module import between orchestrators and scorers

**Domain 2 — Orchestrators (5 additional tools):**
- `pyrit_run_crescendo_orchestrator` — Multi-turn escalating attack; innocuous start,
  iterative escalation toward goal; async `attack_id` pattern; sandbox mode support
- `pyrit_run_pair_orchestrator` — PAIR iterative refinement; adapts prompts based on
  target rejections; configurable max iterations
- `pyrit_run_tree_of_attacks_orchestrator` — TAP branching attack tree with pruning;
  configurable branching factor and depth
- `pyrit_run_skeleton_key_orchestrator` — Priming injection to disable safety filters,
  followed by adversarial follow-up prompts
- `pyrit_run_flip_orchestrator` — Character-reversal encoding to bypass surface-form filters

**Domain 3 — Datasets (4 additional tools):**
- `pyrit_create_custom_dataset` — Create dataset from inline JSON prompt array
- `pyrit_import_dataset_from_file` — Import prompts from CSV or JSON file in `/datasets` volume
- `pyrit_list_session_datasets` — List all datasets loaded in the current session
- `pyrit_merge_datasets` — Merge multiple datasets with optional deduplication

**Domain 4 — Scorers (4 additional tools + full routing):**
- `pyrit_configure_llm_scorer` — LLM-as-judge scorer; supports OpenAI, Ollama, Azure,
  Groq; temperature forced to 0.0; cost warning documented in response
- `pyrit_configure_classifier_scorer` — HuggingFace text classifier via `pyrit-scorer`
  sidecar; configurable categories and endpoint URL
- `pyrit_score_attack_results` — Batch scorer with LLM cost guard: returns
  `pending_confirmation` with token estimate; requires `confirm_cost=True` to proceed
- `pyrit_get_score_distribution` — Aggregate jailbreak rate, score buckets, top findings
- `pyrit_score_response` — Extended to route all scorer types (substring, llm, classifier)
  via `_score_with_type`; previously only handled substring
- `_score_llm` / `_score_classifier` — Private async scoring helpers for LLM-as-judge
  (OpenAI-compatible REST) and classifier sidecar (HTTP `/score` endpoint)

**Docker infrastructure:**
- `docker/Dockerfile.scorer` — HuggingFace classifier sidecar image (python:3.11-slim;
  non-root `scorer` user uid 1001; configurable `SCORER_MODEL_NAME`)
- `docker/scorer_app.py` — FastAPI scoring service; `POST /score` and `GET /health`
  endpoints; `return_all_scores=True`; category filtering; startup model load
- `docker/scorer_requirements.txt` — Pinned sidecar dependencies
- `docker-compose.yml` — Added `pyrit-scorer` service under `local-scorer`, `full`,
  and `full-gpu` profiles; 60s start_period healthcheck; `HUGGINGFACE_TOKEN` passthrough
- `docker-compose.yml` — `local-llm-gpu` profile (NVIDIA CUDA via `ollama/ollama:latest`
  with `deploy.resources.reservations.devices`; `nvidia-container-toolkit` required)
- `docker-compose.yml` — `local-llm-amd` profile (AMD ROCm via `ollama/ollama:rocm`;
  `/dev/kfd` and `/dev/dri` device mounts; `HSA_OVERRIDE_GFX_VERSION` passthrough)

**CI/CD:**
- `.github/workflows/build-and-push.yml` — Multi-platform Docker build (`linux/amd64` +
  `linux/arm64`) on merge to `main`; publishes `:latest` and `:sha-<commit>`;
  publishes `:dev` on every push to `develop`

**Code quality:**
- mypy strict mode: zero errors across all 14 source files
- ruff lint: zero warnings; all 22 files formatted to project standard

---

### Added (Phase 1 — Core MCP Server, First Attack End-to-End)

**Application core:**
- `pyrit_mcp/config.py` — `BackendType` enum, `AttackerBackendConfig`, `ScorerBackendConfig`,
  `ServerConfig` dataclasses; two-layer env loading (.env.detected → .env); `validate_config()`
  for fail-fast startup; module-level singleton with `get_config()` / `reset_config()`
- `pyrit_mcp/server.py` — FastMCP entry point; `register_all_tools()` integration; logging to
  stderr; config validation on startup; `main()` console entry point

**Utilities:**
- `pyrit_mcp/utils/db.py` — DuckDB singleton connection; schema init with 5 tables (targets,
  datasets, scorers, attacks, results); `reset_connection()` for test isolation; `execute()` /
  `fetchall()` / `fetchone()` helpers
- `pyrit_mcp/utils/rate_limiter.py` — Async token bucket rate limiter (`TokenBucketRateLimiter`)
  for controlled request pacing
- `pyrit_mcp/utils/formatters.py` — Structured response helpers (`success()`, `error()`,
  `pending()`, `started()`, `redact_key()`) enforcing consistent JSON shape across all tools

**Domain 1 — Target Management (6 tools):**
- `pyrit_configure_http_target` — Register arbitrary HTTP endpoint as target
- `pyrit_configure_openai_target` — Register OpenAI-compatible API as target (Ollama, vLLM, etc.)
- `pyrit_configure_azure_target` — Register Azure OpenAI deployment as target
- `pyrit_list_targets` — List all registered targets in session
- `pyrit_remove_target` — Remove target (requires `confirm=True`)
- `pyrit_test_target_connectivity` — Probe target for reachability before attacks

**Domain 2 — Orchestrators (3 tools, Phase 1 subset):**
- `pyrit_run_prompt_sending_orchestrator` — Fire dataset at target; async background task;
  returns `attack_id` immediately; sandbox mode support; inline scoring support
- `pyrit_get_attack_status` — Poll attack progress (results_recorded / total_prompts)
- `pyrit_cancel_attack` — Cancel running campaign; preserves results collected so far

**Domain 3 — Datasets (3 tools, Phase 1 subset):**
- `pyrit_list_builtin_datasets` — Full catalog of 12 harm-category datasets with counts
- `pyrit_load_dataset` — Load named dataset into session; idempotent upsert; PyRIT fallback
- `pyrit_preview_dataset` — Preview sample prompts without loading

**Domain 4 — Scorers (3 tools, Phase 1 subset):**
- `pyrit_configure_substring_scorer` — Free deterministic keyword/regex scorer; `any`/`all`/`regex`
  match modes
- `pyrit_score_response` — Score a single response text against a configured scorer
- `pyrit_list_scorers` — List all scorers in session

**Domain 5 — Results (8 tools, all):**
- `pyrit_list_attacks` — List all campaigns; filterable by target and status
- `pyrit_get_attack_results` — Paginated result retrieval with optional score filter
- `pyrit_get_successful_jailbreaks` — Return only responses above score threshold
- `pyrit_get_failed_attacks` — Return refused/low-score responses
- `pyrit_export_results_csv` — Export to CSV file
- `pyrit_generate_report` — Return structured JSON for Claude to narrate as vuln report
- `pyrit_compare_attacks` — Diff two attack campaigns by jailbreak rate
- `pyrit_clear_session` — Wipe all session data (requires `confirm=True`)

**Docker infrastructure:**
- `docker/Dockerfile` — Multi-layer production image; non-root `pyrit` user; 5-layer cache-
  optimised build (OS deps → Python deps → PyRIT → app code → entrypoint)
- `docker/entrypoint.sh` — Startup validation, configuration logging, DB dir init, server launch
- `docker-compose.yml` — Full compose stack with 9 profiles: base, local-llm, local-llm-gpu,
  local-llm-amd, dual-ollama, full-llamacpp, full, full-gpu; named volumes; health checks

**Test suite:**
- `tests/conftest.py` — Fully isolated per-test DB reset; `sample_target_id`,
  `sample_dataset_name`, `sample_scorer_id` fixtures
- `tests/test_targets.py` — 16 tests covering all 6 target management tools
- `tests/test_results.py` — 20 tests covering all 8 result tools

### Design Decisions Resolved in Phase 1
- **PyRIT abstraction level**: Thin HTTP wrapper over PyRIT's targets rather than wrapping
  `PromptRequestPiece` directly. Simpler, more flexible, correct for Phase 1.
- **Multi-turn state**: DuckDB persistence chosen over in-memory (restartability wins).
- **`pyrit_generate_report` scope**: Returns raw JSON only. Claude writes report narrative.
  This avoids circular LLM dependencies and keeps the report in Claude's context window.
- **llama.cpp source**: Official `ghcr.io/ggerganov/llama.cpp:server` image used.

---

### Added (Phase 0 — Repository Foundation)
- Repository structure: all directories, gitignore, dockerignore, pre-commit config
- `pyproject.toml` with ruff, mypy, and pytest configuration
- `requirements.txt` and `requirements-dev.txt` with floor-range version pinning
- `MIT LICENSE`
- `scripts/detect_system.sh` — Linux hardware detection (RAM, CPU, NUMA, GPU)
- `scripts/recommend_models.sh` — RAM-tiered model recommendation engine
- `scripts/validate_env.sh` — Pre-flight environment and system optimization check
- `scripts/download_model.sh` — Interactive GGUF downloader via huggingface-cli
- `scripts/benchmark.sh` — Inference tokens/second tester
- `config/model_catalog.json` — Full model registry Tier 1 through Tier 7
- `config/tier_profiles.json` — RAM tier thresholds and recommended configurations
- `Makefile` — All developer and operator commands
- `.env.example` — Complete environment variable documentation
- `.env.docker.example` — Docker Compose specific env var template
- `.github/workflows/ci.yml` — Lint + typecheck + test matrix (Python 3.10/3.11/3.12)
- `.github/workflows/build-and-push.yml` — Multi-platform Docker build on merge to main
- `.github/workflows/release.yml` — Tag-triggered versioned release
- GitHub issue templates and PR template
- `pyrit_mcp/__init__.py` — Package init with version `0.1.0`
- Placeholder test files for all 7 tool domains (CI green from day 1)

---

## [0.1.0] — Unreleased

Initial development version. See [Unreleased] above.

---

[Unreleased]: https://github.com/ncasfl/pyrit-mcp/compare/HEAD...HEAD
