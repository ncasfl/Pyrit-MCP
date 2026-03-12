# Contributing to pyrit-mcp

Thank you for contributing. This guide covers the development setup, code standards,
testing requirements, and pull request process.

---

## Development Setup

### Prerequisites

- Python 3.10, 3.11, or 3.12
- Docker Desktop (Mac/Windows) or Docker Engine (Linux)
- Git

### Clone and install

```bash
git clone https://github.com/ncasfl/pyrit-mcp.git
cd pyrit-mcp
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt -r requirements-dev.txt
pre-commit install
```

### Configure your environment

```bash
cp .env.example .env
# Edit .env with your attacker and scorer backend settings
```

For local development without a live attacker LLM, set `PYRIT_SANDBOX_MODE=true` in `.env`.

---

## Code Standards

### Naming conventions

All MCP tool functions follow the `pyrit_<verb>_<noun>` pattern without exception.
Private helper functions are prefixed with underscore: `_<verb>_<noun>`.

### Tool return values

Every tool returns a structured JSON dict. Never return plain strings.

```python
# Correct
return {"status": "success", "data": result}

# Wrong — never return raw strings
return "Attack started successfully"
```

### Error messages must include a suggestion

```python
return {
    "status": "error",
    "error": str(e),
    "suggestion": "Call pyrit_list_targets to check configured targets, then retry."
}
```

### Async-only I/O

All database, HTTP, and file operations use `async/await`. No synchronous blocking calls.

### Type annotations

All public functions, methods, and class attributes require type annotations.
`mypy` must pass with zero errors.

### Docstrings

All public functions, classes, and modules require docstrings.

---

## Testing

Run the test suite:

```bash
make test          # Unit tests only (fast, no live backends required)
make test-all      # All tests including integration (requires live backends)
```

### Test markers

- `@pytest.mark.unit` — fast, no external dependencies, always run in CI
- `@pytest.mark.integration` — requires live backends, skipped in CI by default

### Coverage requirement

80% minimum coverage. CI will fail below this threshold.

---

## Linting and Formatting

```bash
make lint      # Check — does not modify files
make format    # Auto-fix formatting
make typecheck # mypy type check
```

All three must pass clean before submitting a PR.

---

## Pull Request Process

1. **Branch from `develop`**, not from `main`
   ```bash
   git checkout develop
   git checkout -b feature/your-feature-name
   ```

2. **Follow implementation order** (from Section 19.2 of the project plan):
   - Write failing tests first
   - Implement code to make tests pass
   - Add type annotations
   - Write docstrings
   - Update CHANGELOG.md under Unreleased

3. **All CI checks must pass** before requesting review

4. **PR title format**: `feat: add pyrit_run_crescendo_orchestrator` or `fix: handle timeout in scorer`

5. **One PR per feature or fix** — keep PRs focused and reviewable

6. **PRs merge to `develop`** — `main` only receives merges from `develop` after testing

---

## Release Process

Releases are made by the maintainer. The process:

```bash
make release    # Interactive: prompts for new version, tags, and pushes
```

The `release.yml` workflow automatically:
- Builds multi-platform Docker images
- Tags them as `:v1.2.3` and `:latest`
- Creates a GitHub Release with the relevant CHANGELOG section

---

## Project Architecture Reference

See the comprehensive project plan document for full architecture details including:
- Tool domain specifications (Section 6)
- LLM backend architecture (Section 7)
- RAM-tiered model selection (Section 8)
- Docker architecture (Section 9)
- Coding instructions and patterns (Section 19)
