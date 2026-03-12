# =============================================================================
# PyRIT MCP Server — Production Image
#
# Base: python:3.11-slim (glibc required for PyRIT's compiled dependencies)
# Layers ordered for maximum Docker cache efficiency:
#   1. OS system dependencies (rarely changes)
#   2. Python requirements (changes on dep bumps)
#   3. PyRIT (large package, separate layer)
#   4. Application code (changes most frequently)
#   5. Entrypoint
#
# Security: runs as non-root user 'pyrit' (uid 1000)
# No secrets in any image layer — all credentials via --env-file at runtime
# =============================================================================

FROM python:3.11-slim AS base

# ---------------------------------------------------------------------------
# Layer 1: OS system dependencies
# gcc and build-essential: required by some PyRIT compiled transitive deps
# libgomp1: required by numpy (used by PyRIT's ML scorer components)
# curl: used by entrypoint healthcheck
# ---------------------------------------------------------------------------
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        gcc \
        build-essential \
        libgomp1 \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user that will run the server
RUN groupadd --gid 1000 pyrit \
    && useradd --uid 1000 --gid pyrit --no-create-home --shell /bin/bash pyrit

# Working directory owned by pyrit user
WORKDIR /app
RUN chown pyrit:pyrit /app

# ---------------------------------------------------------------------------
# Layer 2: Python requirements (cached until requirements.txt changes)
# ---------------------------------------------------------------------------
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# ---------------------------------------------------------------------------
# Layer 3: PyRIT (large package — separate layer to preserve cache)
# This layer only busts when the PyRIT version in requirements.txt changes.
# ---------------------------------------------------------------------------
RUN pip install --no-cache-dir "pyrit>=0.5.0"

# ---------------------------------------------------------------------------
# Layer 4: Application code (changes most frequently)
# ---------------------------------------------------------------------------
COPY --chown=pyrit:pyrit pyrit_mcp/ ./pyrit_mcp/

# ---------------------------------------------------------------------------
# Layer 5: Entrypoint script
# ---------------------------------------------------------------------------
COPY --chown=pyrit:pyrit docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# ---------------------------------------------------------------------------
# Runtime volumes
# /data     — DuckDB session database (bind-mount from host for persistence)
# /datasets — Optional custom prompt dataset CSV/JSON files
# /models   — GGUF model files (read-only bind-mount from host)
# ---------------------------------------------------------------------------
RUN mkdir -p /data /datasets /models \
    && chown pyrit:pyrit /data /datasets /models

# Switch to non-root user
USER pyrit

# MCP over stdio — no network ports exposed
# The -i flag (not -t) keeps stdin open for MCP protocol
CMD ["/entrypoint.sh"]
