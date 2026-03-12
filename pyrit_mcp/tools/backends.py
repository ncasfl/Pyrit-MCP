"""
pyrit_mcp.tools.backends -- Backend management MCP tools (Domain 7).

These tools configure, inspect, and test the LLM backends used by PyRIT
for attacker prompt generation and response scoring. Backends can be
switched at runtime without restarting the MCP server.

Security constraint: API keys are referenced by environment variable name
only -- raw key values are never accepted, stored, or returned.

Tools exposed:
  - pyrit_configure_attacker_backend
  - pyrit_configure_scorer_backend
  - pyrit_list_backend_options
  - pyrit_test_backend_connectivity
  - pyrit_estimate_attack_cost
  - pyrit_recommend_models
  - pyrit_pull_ollama_model
  - pyrit_list_ollama_models
  - pyrit_benchmark_backend
"""

from __future__ import annotations

import logging
import time
from typing import Any

import httpx

from pyrit_mcp.config import BackendType, get_config
from pyrit_mcp.utils.formatters import error, pending, redact_key, success

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Cost estimation constants
# ---------------------------------------------------------------------------

_TOKENS_PER_PROMPT_INPUT = 150
_TOKENS_PER_PROMPT_OUTPUT = 200

# Approximate cost per 1K tokens (input/output) by backend type
_COST_PER_1K: dict[str, dict[str, float]] = {
    "openai": {"input": 0.005, "output": 0.015},
    "azure": {"input": 0.005, "output": 0.015},
    "groq": {"input": 0.0005, "output": 0.001},
    "ollama": {"input": 0.0, "output": 0.0},
    "llamacpp": {"input": 0.0, "output": 0.0},
    "lmstudio": {"input": 0.0, "output": 0.0},
}

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _backend_config_dict(role: str) -> dict[str, Any]:
    """Return a safe dict representation of a backend config (keys redacted)."""
    cfg = get_config()
    bc = cfg.attacker if role == "attacker" else cfg.scorer
    return {
        "role": role,
        "backend_type": bc.backend_type.value,
        "base_url": bc.base_url,
        "model": bc.model,
        "api_key_env": bc.api_key_env,
        "api_key_preview": redact_key(bc.api_key) if bc.api_key else "(none)",
    }


def _validate_backend_type(backend_type: str) -> BackendType | None:
    """Return a BackendType if valid, else None."""
    try:
        return BackendType(backend_type.lower())
    except ValueError:
        return None


def _ollama_base_url() -> str:
    """Return the Ollama base URL from the config or a sensible default."""
    cfg = get_config()
    if cfg.attacker.backend_type == BackendType.OLLAMA:
        return cfg.attacker.base_url
    if cfg.scorer.backend_type == BackendType.OLLAMA:
        return cfg.scorer.base_url
    return "http://localhost:11434"


# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------


async def pyrit_configure_attacker_backend(
    backend_type: str,
    model: str,
    base_url: str,
    api_key_env: str = "",
) -> dict[str, Any]:
    """Switch the attacker LLM backend at runtime.

    The attacker backend generates adversarial prompts for red-team testing.
    Changes take effect immediately for all subsequent attack campaigns.

    Args:
        backend_type: Backend provider (e.g. ``ollama``, ``openai``, ``azure``,
            ``groq``, ``llamacpp``, ``lmstudio``).
        model: Model identifier (e.g. ``dolphin-mistral``, ``gpt-4o``).
        base_url: Full base URL of the backend API.
        api_key_env: Name of the environment variable holding the API key.
            Leave blank for local backends that don't require auth.

    Returns:
        Success with the new attacker config (keys redacted), or error.
    """
    bt = _validate_backend_type(backend_type)
    if bt is None:
        valid = [e.value for e in BackendType]
        return error(
            f"Invalid backend_type '{backend_type}'.",
            f"Valid options: {', '.join(valid)}.",
        )

    if not base_url.startswith(("http://", "https://")):
        return error(
            f"Invalid base_url '{base_url}'. Must start with http:// or https://.",
            "Provide a fully-qualified URL including the scheme.",
        )

    cfg = get_config()
    cfg.attacker.backend_type = bt
    cfg.attacker.model = model
    cfg.attacker.base_url = base_url.rstrip("/")
    cfg.attacker.api_key_env = api_key_env

    log.info(
        "Attacker backend updated: type=%s model=%s url=%s key_env=%s",
        bt.value,
        model,
        base_url,
        api_key_env or "(none)",
    )

    return success(
        {
            "message": "Attacker backend updated successfully.",
            **_backend_config_dict("attacker"),
        }
    )


async def pyrit_configure_scorer_backend(
    backend_type: str,
    model: str,
    base_url: str,
    api_key_env: str = "",
) -> dict[str, Any]:
    """Switch the scorer LLM backend at runtime.

    The scorer backend evaluates target responses for harmful content.
    Changes take effect immediately for all subsequent scoring operations.

    Args:
        backend_type: Backend provider (e.g. ``ollama``, ``openai``, ``azure``,
            ``groq``, ``llamacpp``, ``substring``, ``classifier``).
        model: Model identifier (e.g. ``llama3.1:8b``, ``gpt-4o-mini``).
        base_url: Full base URL of the backend API.
        api_key_env: Name of the environment variable holding the API key.
            Leave blank for local backends that don't require auth.

    Returns:
        Success with the new scorer config (keys redacted), or error.
    """
    bt = _validate_backend_type(backend_type)
    if bt is None:
        valid = [e.value for e in BackendType]
        return error(
            f"Invalid backend_type '{backend_type}'.",
            f"Valid options: {', '.join(valid)}.",
        )

    # substring and classifier scorers don't need a base_url
    if bt not in (BackendType.SUBSTRING, BackendType.CLASSIFIER):
        if not base_url.startswith(("http://", "https://")):
            return error(
                f"Invalid base_url '{base_url}'. Must start with http:// or https://.",
                "Provide a fully-qualified URL including the scheme.",
            )

    cfg = get_config()
    cfg.scorer.backend_type = bt
    cfg.scorer.model = model
    cfg.scorer.base_url = base_url.rstrip("/")
    cfg.scorer.api_key_env = api_key_env

    log.info(
        "Scorer backend updated: type=%s model=%s url=%s key_env=%s",
        bt.value,
        model,
        base_url,
        api_key_env or "(none)",
    )

    return success(
        {
            "message": "Scorer backend updated successfully.",
            **_backend_config_dict("scorer"),
        }
    )


async def pyrit_list_backend_options() -> dict[str, Any]:
    """Show available backend types and their current configuration.

    Returns the current attacker and scorer backend settings along with
    a list of all supported backend types. Read-only -- does not change
    any configuration.

    Returns:
        Success with ``attacker``, ``scorer``, and ``available_backends``.
    """
    available = [{"value": e.value, "name": e.name} for e in BackendType]

    return success(
        {
            "attacker": _backend_config_dict("attacker"),
            "scorer": _backend_config_dict("scorer"),
            "available_backends": available,
        }
    )


async def pyrit_test_backend_connectivity(
    backend_role: str,
) -> dict[str, Any]:
    """Verify that a configured backend responds to a lightweight probe.

    Sends a minimal HTTP request appropriate for the backend type and
    reports whether the backend is reachable and the round-trip latency.

    Args:
        backend_role: Which backend to test -- ``attacker`` or ``scorer``.

    Returns:
        Success with ``reachable`` and ``latency_ms``, or error with suggestion.
    """
    if backend_role not in ("attacker", "scorer"):
        return error(
            f"Invalid backend_role '{backend_role}'.",
            "Must be 'attacker' or 'scorer'.",
        )

    cfg = get_config()
    bc = cfg.attacker if backend_role == "attacker" else cfg.scorer
    bt = bc.backend_type
    base_url = bc.base_url.rstrip("/")

    if not base_url:
        return error(
            f"No base_url configured for {backend_role} backend.",
            f"Call pyrit_configure_{backend_role}_backend to set one.",
        )

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            t0 = time.monotonic()

            if bt == BackendType.OLLAMA:
                resp = await client.get(f"{base_url}/api/tags")
            elif bt == BackendType.LLAMACPP:
                resp = await client.get(f"{base_url}/health")
            elif bt in (
                BackendType.OPENAI,
                BackendType.AZURE,
                BackendType.GROQ,
                BackendType.LMSTUDIO,
            ):
                import os

                api_key = os.environ.get(bc.api_key_env, "") if bc.api_key_env else ""
                headers: dict[str, str] = {}
                if api_key:
                    headers["Authorization"] = f"Bearer {api_key}"

                resp = await client.post(
                    f"{base_url}/chat/completions",
                    headers=headers,
                    json={
                        "model": bc.model,
                        "messages": [{"role": "user", "content": "ping"}],
                        "max_tokens": 1,
                    },
                )
            else:
                return error(
                    f"Connectivity probe not implemented for backend type '{bt.value}'.",
                    "Manually verify the endpoint is reachable.",
                )

            latency_ms = round((time.monotonic() - t0) * 1000, 1)
            resp.raise_for_status()

        log.info(
            "Backend connectivity OK: role=%s type=%s latency=%.1fms",
            backend_role,
            bt.value,
            latency_ms,
        )
        return success(
            {
                "backend_role": backend_role,
                "backend_type": bt.value,
                "reachable": True,
                "latency_ms": latency_ms,
            }
        )

    except httpx.ConnectError as exc:
        return error(
            f"Cannot connect to {backend_role} backend at {base_url}: {exc}",
            f"Verify the URL is correct and the service is running. "
            f"Call pyrit_configure_{backend_role}_backend to update.",
        )
    except httpx.TimeoutException:
        return error(
            f"Connection to {backend_role} backend timed out.",
            "Verify the service is running and responsive. Consider increasing timeout.",
        )
    except httpx.HTTPStatusError as exc:
        return error(
            f"Backend returned HTTP {exc.response.status_code}: {exc.response.text[:200]}",
            "Check API key and model configuration.",
        )
    except Exception as exc:
        return error(
            f"Connectivity probe failed: {exc}",
            f"Call pyrit_list_backend_options to verify {backend_role} configuration.",
        )


async def pyrit_estimate_attack_cost(
    dataset_name: str,
    backend_type: str,
) -> dict[str, Any]:
    """Estimate token usage and cost for an attack campaign.

    Looks up the dataset's prompt count and estimates token consumption
    based on average prompt/response lengths. For cloud backends, an
    approximate USD cost is calculated.

    Args:
        dataset_name: Name of a loaded dataset (from pyrit_list_datasets).
        backend_type: The backend type that will be used (e.g. ``openai``,
            ``ollama``). Determines cost-per-token rates.

    Returns:
        Success with ``total_prompts``, ``estimated_tokens``, and
        ``estimated_cost_usd``, or error if dataset not found.
    """
    from pyrit_mcp.utils.db import fetchone

    bt = _validate_backend_type(backend_type)
    if bt is None:
        valid = [e.value for e in BackendType]
        return error(
            f"Invalid backend_type '{backend_type}'.",
            f"Valid options: {', '.join(valid)}.",
        )

    row = fetchone(
        "SELECT prompt_count FROM datasets WHERE name = ?",
        [dataset_name],
    )
    if row is None:
        return error(
            f"Dataset '{dataset_name}' not found.",
            "Call pyrit_list_datasets to see loaded datasets, or pyrit_load_dataset to load one.",
        )

    prompt_count = int(row[0])
    input_tokens = prompt_count * _TOKENS_PER_PROMPT_INPUT
    output_tokens = prompt_count * _TOKENS_PER_PROMPT_OUTPUT
    total_tokens = input_tokens + output_tokens

    rates = _COST_PER_1K.get(bt.value, {"input": 0.0, "output": 0.0})
    estimated_cost = (input_tokens / 1000) * rates["input"] + (output_tokens / 1000) * rates[
        "output"
    ]

    return success(
        {
            "dataset_name": dataset_name,
            "backend_type": bt.value,
            "total_prompts": prompt_count,
            "estimated_input_tokens": input_tokens,
            "estimated_output_tokens": output_tokens,
            "estimated_total_tokens": total_tokens,
            "estimated_cost_usd": round(estimated_cost, 4),
            "note": (
                "Cost is $0.00 for local backends (ollama, llamacpp, lmstudio). "
                "Cloud estimates are approximate and vary by model."
            ),
        }
    )


async def pyrit_recommend_models(
    available_ram_gb: float,
    has_gpu: bool = False,
    gpu_vram_gb: float = 0,
    role: str = "both",
) -> dict[str, Any]:
    """Return ranked model recommendations based on available hardware.

    Delegates to the system_detect module which analyses hardware constraints
    and returns models that will fit within memory limits.

    Args:
        available_ram_gb: Available system RAM in gigabytes.
        has_gpu: Whether a CUDA/ROCm-capable GPU is available.
        gpu_vram_gb: Available GPU VRAM in gigabytes (0 if no GPU).
        role: Which role to recommend for -- ``attacker``, ``scorer``, or
            ``both`` (default).

    Returns:
        Success with ranked model recommendations, or error.
    """
    if role not in ("attacker", "scorer", "both"):
        return error(
            f"Invalid role '{role}'.",
            "Must be 'attacker', 'scorer', or 'both'.",
        )

    if available_ram_gb <= 0:
        return error(
            "available_ram_gb must be a positive number.",
            "Provide the amount of available RAM in gigabytes (e.g. 16).",
        )

    try:
        from pyrit_mcp.utils.system_detect import recommend_models as _recommend

        recommendations = _recommend(
            available_ram_gb=available_ram_gb,
            has_gpu=has_gpu,
            gpu_vram_gb=gpu_vram_gb,
            role=role,
        )
    except ImportError:
        return error(
            "system_detect module is not available.",
            "Ensure pyrit_mcp.utils.system_detect is installed.",
        )
    except Exception as exc:
        return error(
            f"Model recommendation failed: {exc}",
            "Check that hardware parameters are reasonable values.",
        )

    return success(
        {
            "available_ram_gb": available_ram_gb,
            "has_gpu": has_gpu,
            "gpu_vram_gb": gpu_vram_gb,
            "role": role,
            "recommendations": recommendations,
        }
    )


async def pyrit_pull_ollama_model(
    model_name: str,
    confirm_size_gb: bool = False,
) -> dict[str, Any]:
    """Pull a model into the local Ollama instance.

    Downloads the specified model from the Ollama registry. Requires explicit
    confirmation because model downloads can be several gigabytes.

    Args:
        model_name: Ollama model tag (e.g. ``dolphin-mistral``, ``llama3.1:8b``).
        confirm_size_gb: Must be True to start the download. If False, returns
            a pending-confirmation response.

    Returns:
        Pending confirmation if not confirmed. Success with pull status if
        confirmed. Error if the Ollama API is unreachable.
    """
    if not confirm_size_gb:
        return pending(
            f"Model pull requires confirmation. Pulling '{model_name}' may download "
            "several GB of data. Re-call with confirm_size_gb=true to proceed.",
        )

    base_url = _ollama_base_url().rstrip("/")

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{base_url}/api/pull",
                json={"name": model_name},
            )
            resp.raise_for_status()
            result = resp.text
    except httpx.ConnectError as exc:
        return error(
            f"Cannot connect to Ollama at {base_url}: {exc}",
            "Verify Ollama is running. Start it with 'ollama serve' or check Docker.",
        )
    except httpx.TimeoutException:
        return error(
            f"Ollama pull request timed out for model '{model_name}'.",
            "The model may be very large. Try pulling directly with 'ollama pull'.",
        )
    except httpx.HTTPStatusError as exc:
        return error(
            f"Ollama returned HTTP {exc.response.status_code}: {exc.response.text[:200]}",
            "Verify the model name is correct (e.g. 'dolphin-mistral', 'llama3.1:8b').",
        )
    except Exception as exc:
        return error(
            f"Ollama pull failed: {exc}",
            "Check that Ollama is running and accessible.",
        )

    log.info("Ollama model pull completed: %s", model_name)
    return success(
        {
            "model_name": model_name,
            "message": f"Model '{model_name}' pulled successfully.",
            "raw_response": result[:500],
        }
    )


async def pyrit_list_ollama_models() -> dict[str, Any]:
    """List all models available in the local Ollama instance.

    Queries the Ollama API for installed models and returns their names,
    sizes, and modification dates.

    Returns:
        Success with list of models, or error if Ollama is unreachable.
    """
    base_url = _ollama_base_url().rstrip("/")

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{base_url}/api/tags")
            resp.raise_for_status()
            data = resp.json()
    except httpx.ConnectError as exc:
        return error(
            f"Cannot connect to Ollama at {base_url}: {exc}",
            "Verify Ollama is running. Start it with 'ollama serve' or check Docker.",
        )
    except httpx.TimeoutException:
        return error(
            "Ollama API timed out.",
            "Verify Ollama is running and responsive.",
        )
    except Exception as exc:
        return error(
            f"Failed to list Ollama models: {exc}",
            "Check that Ollama is running and accessible.",
        )

    models = []
    for m in data.get("models", []):
        models.append(
            {
                "name": m.get("name", ""),
                "size_bytes": m.get("size", 0),
                "size_gb": round(m.get("size", 0) / (1024**3), 2),
                "modified_at": m.get("modified_at", ""),
                "digest": m.get("digest", "")[:12],
            }
        )

    return success(
        {
            "models": models,
            "count": len(models),
            "ollama_url": base_url,
        }
    )


async def pyrit_benchmark_backend(
    backend_role: str,
    n_tokens: int = 100,
) -> dict[str, Any]:
    """Run an inference speed test against a configured backend.

    Sends a test prompt requesting the specified number of output tokens
    and measures wall-clock time to compute tokens per second.

    Args:
        backend_role: Which backend to benchmark -- ``attacker`` or ``scorer``.
        n_tokens: Number of tokens to request in the response (default 100).

    Returns:
        Success with ``tokens_per_sec``, ``elapsed_seconds``, and
        ``n_tokens``, or error with suggestion.
    """
    if backend_role not in ("attacker", "scorer"):
        return error(
            f"Invalid backend_role '{backend_role}'.",
            "Must be 'attacker' or 'scorer'.",
        )

    if n_tokens < 1:
        return error(
            "n_tokens must be at least 1.",
            "Provide a positive integer for the number of tokens to generate.",
        )

    import os

    cfg = get_config()
    bc = cfg.attacker if backend_role == "attacker" else cfg.scorer
    base_url = bc.base_url.rstrip("/")

    if not base_url:
        return error(
            f"No base_url configured for {backend_role} backend.",
            f"Call pyrit_configure_{backend_role}_backend to set one.",
        )

    api_key = os.environ.get(bc.api_key_env, "") if bc.api_key_env else ""
    headers: dict[str, str] = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    # Determine the completions endpoint based on backend type
    if bc.backend_type == BackendType.OLLAMA:
        url = f"{base_url}/api/chat"
        payload: dict[str, Any] = {
            "model": bc.model,
            "messages": [
                {
                    "role": "user",
                    "content": f"Count from 1 to {n_tokens}. Output only numbers separated by spaces.",
                }
            ],
            "stream": False,
        }
    elif bc.backend_type == BackendType.LLAMACPP:
        url = f"{base_url}/v1/chat/completions"
        payload = {
            "messages": [
                {
                    "role": "user",
                    "content": f"Count from 1 to {n_tokens}. Output only numbers separated by spaces.",
                }
            ],
            "max_tokens": n_tokens,
        }
    else:
        url = f"{base_url}/chat/completions"
        payload = {
            "model": bc.model,
            "messages": [
                {
                    "role": "user",
                    "content": f"Count from 1 to {n_tokens}. Output only numbers separated by spaces.",
                }
            ],
            "max_tokens": n_tokens,
        }

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            t0 = time.monotonic()
            resp = await client.post(url, headers=headers, json=payload)
            elapsed = time.monotonic() - t0
            resp.raise_for_status()
            data = resp.json()
    except httpx.ConnectError as exc:
        return error(
            f"Cannot connect to {backend_role} backend at {base_url}: {exc}",
            "Verify the service is running. Call pyrit_test_backend_connectivity first.",
        )
    except httpx.TimeoutException:
        return error(
            f"Benchmark timed out after 60s for {backend_role} backend.",
            "The backend may be overloaded. Try with fewer tokens.",
        )
    except httpx.HTTPStatusError as exc:
        return error(
            f"Backend returned HTTP {exc.response.status_code}: {exc.response.text[:200]}",
            "Check API key and model configuration.",
        )
    except Exception as exc:
        return error(
            f"Benchmark failed: {exc}",
            f"Call pyrit_test_backend_connectivity to verify the {backend_role} backend.",
        )

    # Extract actual token count from response
    usage = data.get("usage", {})
    completion_tokens = usage.get("completion_tokens", n_tokens)

    # Ollama API returns different structure
    if bc.backend_type == BackendType.OLLAMA and "eval_count" in data:
        completion_tokens = data["eval_count"]

    tokens_per_sec = round(completion_tokens / elapsed, 1) if elapsed > 0 else 0

    log.info(
        "Benchmark complete: role=%s type=%s tokens=%d elapsed=%.2fs tps=%.1f",
        backend_role,
        bc.backend_type.value,
        completion_tokens,
        elapsed,
        tokens_per_sec,
    )

    return success(
        {
            "backend_role": backend_role,
            "backend_type": bc.backend_type.value,
            "model": bc.model,
            "n_tokens_requested": n_tokens,
            "completion_tokens": completion_tokens,
            "elapsed_seconds": round(elapsed, 2),
            "tokens_per_sec": tokens_per_sec,
        }
    )
