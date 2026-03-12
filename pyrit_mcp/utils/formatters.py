"""
pyrit_mcp.utils.formatters — Structured JSON response helpers.

Every MCP tool returns a structured dict. These helpers enforce consistent
response shape so Claude always knows what keys to expect.

Success response shape::

    {
        "status": "success",
        "data": { ... }        # tool-specific payload
    }

Error response shape::

    {
        "status": "error",
        "error": "...",        # human-readable error description
        "suggestion": "..."    # next actionable step for Claude
    }

Pending-confirmation response shape (used before destructive actions)::

    {
        "status": "pending_confirmation",
        "message": "...",      # what will happen if confirmed
        "estimate": { ... }    # optional cost/impact estimate
    }
"""

from __future__ import annotations

from typing import Any


def success(data: dict[str, Any] | list[Any] | str | None = None) -> dict[str, Any]:
    """Return a standard success response dict.

    Args:
        data: Tool-specific payload to include under the ``data`` key.
    """
    return {"status": "success", "data": data}


def error(message: str, suggestion: str = "") -> dict[str, Any]:
    """Return a standard error response dict.

    Args:
        message: What went wrong.
        suggestion: The next tool Claude should call or action to take.
    """
    response: dict[str, Any] = {"status": "error", "error": message}
    if suggestion:
        response["suggestion"] = suggestion
    return response


def pending(message: str, estimate: dict[str, Any] | None = None) -> dict[str, Any]:
    """Return a pending-confirmation response for destructive or costly actions.

    The caller must re-invoke the tool with the appropriate confirm parameter
    set to True before the action proceeds.

    Args:
        message: Description of what will happen if the action is confirmed.
        estimate: Optional cost or impact estimate (e.g. token counts, cost).
    """
    response: dict[str, Any] = {"status": "pending_confirmation", "message": message}
    if estimate is not None:
        response["estimate"] = estimate
    return response


def started(attack_id: str, description: str = "") -> dict[str, Any]:
    """Return a response indicating an async attack campaign has been launched.

    Args:
        attack_id: UUID of the attack campaign. Use with pyrit_get_attack_status.
        description: Optional human-readable description of what was started.
    """
    return {
        "status": "started",
        "attack_id": attack_id,
        "message": (
            f"{description} Poll progress with pyrit_get_attack_status(attack_id='{attack_id}')"
        ).strip(),
    }


def redact_key(value: str) -> str:
    """Redact an API key for safe logging.

    Shows the first 4 and last 2 characters with asterisks in between,
    or fully redacts if the key is too short to partially show safely.
    """
    if not value or len(value) < 8:
        return "[REDACTED]"
    return f"{value[:4]}{'*' * (len(value) - 6)}{value[-2:]}"
