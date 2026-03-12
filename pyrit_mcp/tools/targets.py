"""
pyrit_mcp.tools.targets — Target management MCP tools (Domain 1).

These tools configure the AI application being tested. A target must be
registered before any attack campaign can be launched.

Security constraint: credential parameters only accept the NAME of an
environment variable, never the actual key value. This keeps secrets out
of MCP conversation logs and DuckDB session records.

Tools exposed:
  - pyrit_configure_http_target
  - pyrit_configure_openai_target
  - pyrit_configure_azure_target
  - pyrit_list_targets
  - pyrit_remove_target
  - pyrit_test_target_connectivity
"""

from __future__ import annotations

import json
import logging
import uuid
from typing import Any

import httpx

from pyrit_mcp.utils.db import execute, fetchall, fetchone
from pyrit_mcp.utils.formatters import error, success

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _row_to_target(row: tuple[Any, ...]) -> dict[str, Any]:
    """Convert a DuckDB targets table row to a safe public dict.

    Parses the JSON config and strips any resolved API key values from the
    output so credentials never appear in tool responses.
    """
    target_id, target_type, config_json_raw, created_at = row
    config = json.loads(config_json_raw) if isinstance(config_json_raw, str) else config_json_raw
    # Never expose resolved API key values — only the env var name
    config.pop("_resolved_key", None)
    return {
        "target_id": str(target_id),
        "target_type": target_type,
        "config": config,
        "created_at": str(created_at),
    }


def _store_target(target_type: str, config: dict[str, Any]) -> str:
    """Persist a target config to the DB and return its UUID."""
    target_id = str(uuid.uuid4())
    execute(
        "INSERT INTO targets (target_id, target_type, config_json) VALUES (?, ?, ?)",
        [target_id, target_type, json.dumps(config)],
    )
    log.info("Registered target %s (type=%s)", target_id, target_type)
    return target_id


# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------


async def pyrit_configure_http_target(
    url: str,
    headers: str | None = None,
    request_template: str | None = None,
    response_path: str | None = None,
    api_key_env: str | None = None,
) -> dict[str, Any]:
    """Register an arbitrary HTTP endpoint as a target for red-team testing.

    Use this for custom APIs, REST endpoints, or any HTTP service that accepts
    natural-language input. The request_template uses ``{prompt}`` as the
    placeholder for the injected test prompt.

    Args:
        url: Full URL of the HTTP endpoint (e.g. https://api.example.com/chat).
        headers: JSON string of headers dict (e.g. '{"Content-Type":"application/json"}').
        request_template: JSON body template with ``{prompt}`` placeholder.
            Default: ``{"message": "{prompt}"}``.
        response_path: Dot-separated path to extract the response text
            (e.g. ``choices.0.message.content``). Default: reads full response body.
        api_key_env: Name of the environment variable holding the Bearer token.
            The actual key value is NEVER accepted as a parameter.

    Returns:
        Success with ``target_id`` UUID, or error with suggestion.
    """
    if not url.startswith(("http://", "https://")):
        return error(
            f"Invalid URL '{url}'. Must start with http:// or https://.",
            "Provide a fully-qualified URL including the scheme.",
        )

    parsed_headers: dict[str, str] = {}
    if headers:
        try:
            parsed_headers = json.loads(headers)
        except json.JSONDecodeError as exc:
            return error(
                f"Invalid JSON in headers parameter: {exc}",
                'Pass headers as a valid JSON string, e.g. \'{"Authorization": "Bearer token"}\'',
            )

    config: dict[str, Any] = {
        "url": url,
        "headers": parsed_headers,
        "request_template": request_template or '{"message": "{prompt}"}',
        "response_path": response_path or "",
        "api_key_env": api_key_env or "",
    }

    target_id = _store_target("http", config)
    return success(
        {
            "target_id": target_id,
            "target_type": "http",
            "url": url,
            "message": (
                f"HTTP target registered. Use target_id '{target_id}' "
                "when launching attack campaigns."
            ),
        }
    )


async def pyrit_configure_openai_target(
    api_base: str,
    model: str,
    api_key_env: str = "",
    system_prompt: str | None = None,
    temperature: float = 0.7,
    max_tokens: int = 1024,
) -> dict[str, Any]:
    """Register an OpenAI-compatible API endpoint as a target.

    Works with OpenAI, Ollama, LM Studio, vLLM, llama.cpp server, Groq, or any
    provider that speaks the OpenAI chat completions API.

    Args:
        api_base: Base URL of the API (e.g. http://localhost:11434 for Ollama,
            https://api.openai.com/v1 for OpenAI).
        model: Model identifier string (e.g. ``gpt-4o``, ``llama3.1:8b``).
        api_key_env: Name of the environment variable holding the API key.
            Leave blank for local endpoints like Ollama that don't require auth.
        system_prompt: Optional system prompt to prepend to every request.
        temperature: Sampling temperature (0.0-2.0). Higher = more varied outputs.
        max_tokens: Maximum tokens in the target's response.

    Returns:
        Success with ``target_id`` UUID, or error with suggestion.
    """
    if not api_base.startswith(("http://", "https://")):
        return error(
            f"Invalid api_base '{api_base}'. Must start with http:// or https://.",
            "For Ollama, use http://ollama:11434 (Docker) or http://localhost:11434 (local).",
        )

    config: dict[str, Any] = {
        "api_base": api_base.rstrip("/"),
        "model": model,
        "api_key_env": api_key_env,
        "system_prompt": system_prompt or "",
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    target_id = _store_target("openai", config)
    return success(
        {
            "target_id": target_id,
            "target_type": "openai",
            "api_base": api_base,
            "model": model,
            "message": (
                f"OpenAI-compatible target registered. Use target_id '{target_id}' "
                "when launching attack campaigns."
            ),
        }
    )


async def pyrit_configure_azure_target(
    deployment_name: str,
    endpoint_env: str = "AZURE_OPENAI_ENDPOINT",
    api_key_env: str = "AZURE_OPENAI_API_KEY",
    api_version: str = "2024-02-01",
    system_prompt: str | None = None,
    content_filter_override: bool = False,
) -> dict[str, Any]:
    """Register an Azure OpenAI deployment as a target.

    For enterprise environments where the target application runs on Azure.
    The endpoint and API key are read from environment variables.

    Args:
        deployment_name: Azure OpenAI deployment name (not the model name).
        endpoint_env: Name of the env var holding the Azure endpoint URL.
            Default: ``AZURE_OPENAI_ENDPOINT``.
        api_key_env: Name of the env var holding the Azure API key.
            Default: ``AZURE_OPENAI_API_KEY``.
        api_version: Azure OpenAI API version string.
        system_prompt: Optional system prompt prepended to every request.
        content_filter_override: Set True only if you have enrolled in
            Microsoft's Limited Access content filter bypass program.

    Returns:
        Success with ``target_id`` UUID, or error with suggestion.
    """
    import os

    endpoint = os.environ.get(endpoint_env, "")
    if not endpoint:
        return error(
            f"Environment variable '{endpoint_env}' is not set.",
            f"Set {endpoint_env}=https://your-resource.openai.azure.com in your .env file.",
        )

    config: dict[str, Any] = {
        "deployment_name": deployment_name,
        "endpoint_env": endpoint_env,
        "api_key_env": api_key_env,
        "api_version": api_version,
        "system_prompt": system_prompt or "",
        "content_filter_override": content_filter_override,
    }

    target_id = _store_target("azure", config)
    return success(
        {
            "target_id": target_id,
            "target_type": "azure",
            "deployment_name": deployment_name,
            "message": (
                f"Azure OpenAI target registered. Use target_id '{target_id}' "
                "when launching attack campaigns."
            ),
        }
    )


async def pyrit_list_targets() -> dict[str, Any]:
    """List all targets configured in the current session.

    Returns all registered targets with their IDs, types, and configs.
    Use target IDs from this list when launching attack campaigns.

    Returns:
        Success with list of target dicts, each containing ``target_id``,
        ``target_type``, ``config``, and ``created_at``.
    """
    rows = fetchall(
        "SELECT target_id, target_type, config_json, created_at FROM targets ORDER BY created_at"
    )
    targets = [_row_to_target(row) for row in rows]
    return success(
        {
            "targets": targets,
            "count": len(targets),
        }
    )


async def pyrit_remove_target(target_id: str, confirm: bool = False) -> dict[str, Any]:
    """Remove a registered target by ID.

    This is a destructive operation: the target configuration is permanently
    deleted from the session database. Active attacks using this target are
    not affected, but new attacks cannot be launched against this target.

    Args:
        target_id: UUID of the target to remove (from pyrit_list_targets).
        confirm: Must be True to execute the deletion. If False, returns a
            preview of what will be deleted.

    Returns:
        Error if target not found. Pending-confirmation if confirm=False.
        Success with deletion confirmation if confirm=True.
    """
    from pyrit_mcp.utils.formatters import pending

    row = fetchone(
        "SELECT target_id, target_type, config_json FROM targets WHERE target_id = ?",
        [target_id],
    )
    if row is None:
        return error(
            f"Target '{target_id}' not found.",
            "Call pyrit_list_targets to see all registered targets.",
        )

    target_type = row[1]

    if not confirm:
        return pending(
            f"Will permanently delete {target_type} target '{target_id}'. "
            "Re-call with confirm=true to proceed.",
        )

    execute("DELETE FROM targets WHERE target_id = ?", [target_id])
    log.info("Deleted target %s", target_id)
    return success(
        {
            "deleted": True,
            "target_id": target_id,
            "message": f"Target '{target_id}' deleted from session.",
        }
    )


async def pyrit_test_target_connectivity(
    target_id: str,
    probe_prompt: str = "Hello, please respond with the single word: CONNECTED",
) -> dict[str, Any]:
    """Send a lightweight probe to verify a target is reachable and responding.

    Tests HTTP connectivity and basic request/response round-trip. This does
    NOT run through PyRIT orchestration — it is a direct connectivity check.

    Args:
        target_id: UUID of the target to probe (from pyrit_list_targets).
        probe_prompt: The text to send as the test message.

    Returns:
        Success with connectivity status and response preview, or error.
    """
    row = fetchone(
        "SELECT target_id, target_type, config_json FROM targets WHERE target_id = ?",
        [target_id],
    )
    if row is None:
        return error(
            f"Target '{target_id}' not found.",
            "Call pyrit_list_targets to see all registered targets.",
        )

    target_type = row[1]
    config = json.loads(row[2]) if isinstance(row[2], str) else row[2]

    try:
        if target_type == "openai":
            result = await _probe_openai_target(config, probe_prompt)
        elif target_type == "http":
            result = await _probe_http_target(config, probe_prompt)
        elif target_type == "azure":
            result = await _probe_azure_target(config, probe_prompt)
        else:
            return error(
                f"Connectivity probe not implemented for target type '{target_type}'.",
                "Manually verify the endpoint is reachable.",
            )

        return success(
            {
                "target_id": target_id,
                "target_type": target_type,
                "reachable": True,
                "response_preview": result[:200] if result else "(empty response)",
            }
        )

    except httpx.ConnectError as exc:
        return error(
            f"Cannot connect to target: {exc}",
            "Verify the target URL is correct and the service is running.",
        )
    except httpx.TimeoutException:
        return error(
            "Connection timed out.",
            "Increase ATTACKER_TIMEOUT in .env or verify the target is responsive.",
        )
    except Exception as exc:
        return error(
            f"Probe failed: {exc}",
            "Check target configuration with pyrit_list_targets.",
        )


async def _probe_openai_target(config: dict[str, Any], prompt: str) -> str:
    """Send a test message to an OpenAI-compatible target."""
    import os

    api_base = config["api_base"]
    model = config["model"]
    api_key = os.environ.get(config.get("api_key_env", ""), "ollama")
    system_prompt = config.get("system_prompt", "")

    messages: list[dict[str, str]] = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(
            f"{api_base}/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={"model": model, "messages": messages, "max_tokens": 50},
        )
        resp.raise_for_status()
        data = resp.json()
        return str(data["choices"][0]["message"]["content"])


async def _probe_http_target(config: dict[str, Any], prompt: str) -> str:
    """Send a test request to an HTTP target."""
    import os

    url = config["url"]
    headers = dict(config.get("headers", {}))
    template = config.get("request_template", '{"message": "{prompt}"}')
    api_key_env = config.get("api_key_env", "")
    if api_key_env:
        api_key = os.environ.get(api_key_env, "")
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

    body_str = template.replace("{prompt}", prompt)
    try:
        body = json.loads(body_str)
    except json.JSONDecodeError:
        body = {"message": prompt}

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(url, headers=headers, json=body)
        resp.raise_for_status()
        return resp.text[:200]


async def _probe_azure_target(config: dict[str, Any], prompt: str) -> str:
    """Send a test request to an Azure OpenAI target."""
    import os

    endpoint = os.environ.get(config.get("endpoint_env", "AZURE_OPENAI_ENDPOINT"), "")
    api_key = os.environ.get(config.get("api_key_env", "AZURE_OPENAI_API_KEY"), "")
    deployment = config["deployment_name"]
    api_version = config.get("api_version", "2024-02-01")

    url = f"{endpoint}/openai/deployments/{deployment}/chat/completions?api-version={api_version}"
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(
            url,
            headers={"api-key": api_key},
            json={"messages": [{"role": "user", "content": prompt}], "max_tokens": 50},
        )
        resp.raise_for_status()
        data = resp.json()
        return str(data["choices"][0]["message"]["content"])
