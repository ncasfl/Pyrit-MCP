# =============================================================================
# PyRIT MCP Server — Makefile
#
# All developer and operator commands. Run 'make help' for usage.
#
# NOTE: Shell scripts (detect, recommend, validate-env) are designed to run
# on the Linux deployment machine, NOT on Windows. On Windows, these targets
# will print a notice and skip. Docker targets work on all platforms.
# =============================================================================

.DEFAULT_GOAL := help
SHELL := /bin/bash

# ── Project config ────────────────────────────────────────────────────────────
PROJECT      := pyrit-mcp
REGISTRY     := ghcr.io/ncasfl
IMAGE        := $(REGISTRY)/$(PROJECT)
VERSION      := $(shell grep '__version__' pyrit_mcp/__init__.py | cut -d'"' -f2)
COMPOSE      := docker compose
COMPOSE_DEV  := docker compose -f docker-compose.yml -f docker-compose.dev.yml

# Auto-detect compose profile from .env.detected if available
DETECTED_PROFILE ?= $(shell grep 'RECOMMENDED_COMPOSE_PROFILE=' .env.detected 2>/dev/null | cut -d= -f2)
COMPOSE_PROFILE  ?= $(if $(DETECTED_PROFILE),$(DETECTED_PROFILE),local-llm)

# ── OS detection for Linux-only targets ───────────────────────────────────────
IS_LINUX := $(shell uname -s 2>/dev/null | grep -c Linux || true)

.PHONY: help
help: ## Show this help message
	@echo ""
	@echo "  PyRIT MCP Server — Developer Commands"
	@echo "  ======================================"
	@echo ""
	@echo "  Setup:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | grep -E '(detect|recommend|setup|validate|download)' | \
		awk 'BEGIN{FS=":.*?## "}{printf "    %-22s %s\n", $$1, $$2}'
	@echo ""
	@echo "  Docker:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | grep -E '(build|up|down|logs|shell|pull)' | \
		awk 'BEGIN{FS=":.*?## "}{printf "    %-22s %s\n", $$1, $$2}'
	@echo ""
	@echo "  Development:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | grep -E '(test|lint|typecheck|benchmark)' | \
		awk 'BEGIN{FS=":.*?## "}{printf "    %-22s %s\n", $$1, $$2}'
	@echo ""
	@echo "  Release:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | grep -E '(release|clean)' | \
		awk 'BEGIN{FS=":.*?## "}{printf "    %-22s %s\n", $$1, $$2}'
	@echo ""

# =============================================================================
# SETUP TARGETS
# =============================================================================

.PHONY: detect
detect: ## Detect system hardware and write .env.detected (Linux only)
ifeq ($(IS_LINUX),1)
	@chmod +x scripts/detect_system.sh
	@scripts/detect_system.sh
else
	@echo ""
	@echo "  NOTE: 'make detect' is designed for Linux deployment machines."
	@echo "  This is your Windows development machine — detection is not applicable here."
	@echo "  Run 'make detect' on the Linux server where Docker will be deployed."
	@echo ""
endif

.PHONY: recommend
recommend: ## Read .env.detected and write model recommendations (Linux only)
ifeq ($(IS_LINUX),1)
	@chmod +x scripts/recommend_models.sh
	@scripts/recommend_models.sh
else
	@echo ""
	@echo "  NOTE: 'make recommend' is designed for Linux deployment machines."
	@echo "  Run 'make recommend' on the Linux server after running 'make detect'."
	@echo ""
endif

.PHONY: setup
setup: detect recommend validate-env ## Full setup: detect + recommend + validate (Linux only)
	@echo "Setup complete. Next: copy .env.example to .env and configure it."

.PHONY: validate-env
validate-env: ## Validate environment variables and system settings
ifeq ($(IS_LINUX),1)
	@chmod +x scripts/validate_env.sh
	@scripts/validate_env.sh
else
	@echo "  NOTE: Full env validation runs on Linux. Skipping system checks."
	@echo "  Ensure .env is configured before deploying to Linux."
endif

.PHONY: download-model
download-model: ## Interactive GGUF model downloader (requires huggingface-hub)
	@chmod +x scripts/download_model.sh
	@scripts/download_model.sh

# =============================================================================
# DOCKER TARGETS
# =============================================================================

.PHONY: build
build: ## Build all Docker images
	$(COMPOSE) build

.PHONY: up
up: ## Start with auto-detected profile (from .env.detected) or local-llm default
	@echo "Starting with profile: $(COMPOSE_PROFILE)"
	$(COMPOSE) --profile $(COMPOSE_PROFILE) up -d
	@echo "Started. Logs: make logs"

.PHONY: up-gpu
up-gpu: ## Start with NVIDIA GPU-accelerated Ollama
	$(COMPOSE) --profile local-llm-gpu up -d

.PHONY: up-amd
up-amd: ## Start with AMD ROCm GPU-accelerated Ollama
	$(COMPOSE) --profile local-llm-amd up -d

.PHONY: up-dual
up-dual: ## Start with dual Ollama instances (independent attacker + scorer)
	$(COMPOSE) --profile dual-ollama up -d

.PHONY: up-llamacpp
up-llamacpp: ## Start with llama.cpp attacker + Ollama scorer (Tier 5/6/7)
	$(COMPOSE) --profile full-llamacpp up -d

.PHONY: up-full
up-full: ## Start fully offline CPU stack
	$(COMPOSE) --profile full up -d

.PHONY: up-dev
up-dev: ## Start in dev mode with hot reload
	$(COMPOSE_DEV) --profile local-llm up

.PHONY: down
down: ## Stop all containers
	$(COMPOSE) down

.PHONY: logs
logs: ## Follow container logs
	$(COMPOSE) logs -f

.PHONY: shell
shell: ## Open a shell in the running pyrit-mcp container
	docker exec -it $$(docker compose ps -q pyrit-mcp) /bin/bash

.PHONY: pull-latest
pull-latest: ## Pull the latest image from ghcr.io
	docker pull $(IMAGE):latest

# =============================================================================
# DEVELOPMENT TARGETS
# =============================================================================

.PHONY: install
install: ## Install all dependencies in the current Python environment
	pip install -r requirements.txt -r requirements-dev.txt
	pre-commit install

.PHONY: test
test: ## Run the full test suite with coverage
	pytest tests/ --cov=pyrit_mcp --cov-report=term-missing -m "not integration"

.PHONY: test-all
test-all: ## Run ALL tests including integration tests (requires live backends)
	pytest tests/ --cov=pyrit_mcp --cov-report=term-missing

.PHONY: lint
lint: ## Run ruff linter and format check
	ruff check pyrit_mcp/ tests/
	ruff format --check pyrit_mcp/ tests/

.PHONY: format
format: ## Auto-fix formatting with ruff
	ruff check --fix pyrit_mcp/ tests/
	ruff format pyrit_mcp/ tests/

.PHONY: typecheck
typecheck: ## Run mypy type checker
	mypy pyrit_mcp/

.PHONY: benchmark
benchmark: ## Run inference speed test on configured backend
	@chmod +x scripts/benchmark.sh
	@scripts/benchmark.sh

# =============================================================================
# RELEASE TARGETS
# =============================================================================

.PHONY: release
release: ## Bump version, update CHANGELOG, tag, and push (interactive)
	@echo "Current version: $(VERSION)"
	@read -p "New version (e.g. 1.1.0): " NEW_VERSION; \
	sed -i "s/__version__ = \"$(VERSION)\"/__version__ = \"$$NEW_VERSION\"/" pyrit_mcp/__init__.py; \
	sed -i "s/version = \"$(VERSION)\"/version = \"$$NEW_VERSION\"/" pyproject.toml; \
	git add pyrit_mcp/__init__.py pyproject.toml CHANGELOG.md; \
	git commit -m "chore: release v$$NEW_VERSION"; \
	git tag -a "v$$NEW_VERSION" -m "Release v$$NEW_VERSION"; \
	git push origin main "v$$NEW_VERSION"; \
	echo "Tagged and pushed v$$NEW_VERSION"

# =============================================================================
# CLEANUP TARGETS
# =============================================================================

.PHONY: clean
clean: ## Remove containers and named volumes (preserves GGUF model files)
	$(COMPOSE) down -v
	@echo "Containers and volumes removed. Model files preserved in ./models/"

.PHONY: clean-models
clean-models: ## Remove downloaded GGUF files from ./models/ (prompts confirmation)
	@echo "WARNING: This will delete all GGUF files in ./models/"
	@ls -lh models/*.gguf 2>/dev/null || echo "  (no .gguf files found)"
	@read -p "Delete all GGUF files? [y/N]: " CONFIRM; \
	if [ "$$CONFIRM" = "y" ]; then \
		rm -f models/*.gguf; \
		echo "Model files removed."; \
	else \
		echo "Aborted."; \
	fi

.PHONY: clean-all
clean-all: clean clean-models ## Remove everything including model files
