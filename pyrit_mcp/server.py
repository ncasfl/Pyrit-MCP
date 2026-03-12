"""
pyrit_mcp.server — FastMCP entry point for the PyRIT MCP server.

This module creates the FastMCP instance, registers all tool functions,
validates configuration on startup, and provides the main() entry point.

The server communicates over stdio (MCP standard transport) — it binds
to no network ports and requires no separate daemon process.

Usage (Claude Desktop / Claude Code):
    command: docker run --rm -i --env-file .env ghcr.io/ncasfl/pyrit-mcp:latest

Usage (direct Python):
    python -m pyrit_mcp.server
    or: pyrit-mcp  (via pyproject.toml console_scripts entry point)
"""

from __future__ import annotations

import logging
import sys

from mcp.server.fastmcp import FastMCP

from pyrit_mcp import __version__
from pyrit_mcp.config import get_config, validate_config
from pyrit_mcp.tools import register_all_tools

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------


def _configure_logging(level: str) -> None:
    """Configure root logger to stderr so logs do not pollute MCP stdio."""
    logging.basicConfig(
        stream=sys.stderr,
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)-8s %(name)s — %(message)s",
        datefmt="%H:%M:%S",
    )


# ---------------------------------------------------------------------------
# FastMCP instance
# ---------------------------------------------------------------------------

mcp = FastMCP(
    name="pyrit-mcp",
    instructions=(
        "You are operating the PyRIT MCP server — an AI red-teaming platform. "
        "Use the available tools to: configure target applications, load adversarial "
        "datasets, run attack campaigns, score results, and generate vulnerability reports. "
        "\n\n"
        "RECOMMENDED WORKFLOW:\n"
        "1. pyrit_configure_openai_target or pyrit_configure_http_target\n"
        "2. pyrit_test_target_connectivity (verify the target is reachable)\n"
        "3. pyrit_list_builtin_datasets then pyrit_load_dataset\n"
        "4. (optional) pyrit_configure_substring_scorer\n"
        "5. pyrit_run_prompt_sending_orchestrator\n"
        "6. pyrit_get_attack_status (poll until complete)\n"
        "7. pyrit_get_successful_jailbreaks and pyrit_generate_report\n"
        "\n"
        "SAFETY: Always have explicit written authorisation before testing any target. "
        "Set PYRIT_SANDBOX_MODE=true to run a dry-run without sending real requests."
    ),
)

register_all_tools(mcp)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """Validate configuration and start the MCP server over stdio."""
    config = get_config()
    _configure_logging(config.log_level)

    log = logging.getLogger(__name__)
    log.info("PyRIT MCP Server v%s starting", __version__)

    # Validate configuration — fail fast with clear error messages
    errors = validate_config(config)
    if errors:
        for err in errors:
            log.error("Configuration error: %s", err)
        sys.stderr.write(
            "\n[pyrit-mcp] Configuration errors detected. "
            "Fix the above errors in your .env file and restart.\n"
        )
        sys.exit(1)

    log.info(
        "Attacker: %s / %s | Scorer: %s / %s | Sandbox: %s",
        config.attacker.backend_type.value,
        config.attacker.model,
        config.scorer.backend_type.value,
        config.scorer.model or "n/a",
        config.sandbox_mode,
    )

    # Initialise the database (creates tables if first run)
    from pyrit_mcp.utils.db import get_connection

    get_connection()
    log.info("Database initialised at %s", config.db_path)

    # Start the MCP server (blocks until client disconnects)
    log.info("MCP server ready — listening on stdio")
    mcp.run()


if __name__ == "__main__":
    main()
