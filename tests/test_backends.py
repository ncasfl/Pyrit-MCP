"""Tests for pyrit_mcp backend management tools (Domain 7).

Tests cover all 9 backend management tools:
  - pyrit_configure_attacker_backend
  - pyrit_configure_scorer_backend
  - pyrit_list_backend_options
  - pyrit_test_backend_connectivity
  - pyrit_estimate_attack_cost
  - pyrit_recommend_models
  - pyrit_pull_ollama_model
  - pyrit_list_ollama_models
  - pyrit_benchmark_backend

All network calls are mocked — no live backends required.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from pyrit_mcp.utils.db import execute

# ---------------------------------------------------------------------------
# pyrit_configure_attacker_backend
# ---------------------------------------------------------------------------


@pytest.mark.unit
async def test_configure_attacker_backend_success() -> None:
    """Switching attacker backend updates the config singleton."""
    from pyrit_mcp.tools.backends import pyrit_configure_attacker_backend

    result = await pyrit_configure_attacker_backend(
        backend_type="ollama",
        model="dolphin-mixtral:8x7b",
        base_url="http://localhost:11434",
    )
    assert result["status"] == "success"
    data = result["data"]
    assert data["backend_type"] == "ollama"
    assert data["model"] == "dolphin-mixtral:8x7b"


@pytest.mark.unit
async def test_configure_attacker_backend_invalid_type() -> None:
    """Invalid backend_type should return an error."""
    from pyrit_mcp.tools.backends import pyrit_configure_attacker_backend

    result = await pyrit_configure_attacker_backend(
        backend_type="invalid_backend",
        model="test",
        base_url="http://localhost:1234",
    )
    assert result["status"] == "error"
    assert "suggestion" in result


@pytest.mark.unit
async def test_configure_attacker_backend_with_api_key_env() -> None:
    """API key env name should be stored, not the actual key value."""
    from pyrit_mcp.tools.backends import pyrit_configure_attacker_backend

    result = await pyrit_configure_attacker_backend(
        backend_type="openai",
        model="gpt-4o",
        base_url="https://api.openai.com/v1",
        api_key_env="MY_OPENAI_KEY",
    )
    assert result["status"] == "success"
    # The actual key value must never appear in the response
    assert "sk-" not in json.dumps(result)


# ---------------------------------------------------------------------------
# pyrit_configure_scorer_backend
# ---------------------------------------------------------------------------


@pytest.mark.unit
async def test_configure_scorer_backend_success() -> None:
    """Switching scorer backend updates the config singleton."""
    from pyrit_mcp.tools.backends import pyrit_configure_scorer_backend

    result = await pyrit_configure_scorer_backend(
        backend_type="ollama",
        model="nous-hermes2",
        base_url="http://localhost:11435",
    )
    assert result["status"] == "success"
    data = result["data"]
    assert data["backend_type"] == "ollama"
    assert data["model"] == "nous-hermes2"


@pytest.mark.unit
async def test_configure_scorer_backend_substring() -> None:
    """Substring scorer requires no base_url or model."""
    from pyrit_mcp.tools.backends import pyrit_configure_scorer_backend

    result = await pyrit_configure_scorer_backend(
        backend_type="substring",
        model="",
        base_url="",
    )
    assert result["status"] == "success"


@pytest.mark.unit
async def test_configure_scorer_backend_invalid_type() -> None:
    """Invalid backend_type should return an error."""
    from pyrit_mcp.tools.backends import pyrit_configure_scorer_backend

    result = await pyrit_configure_scorer_backend(
        backend_type="nonexistent",
        model="test",
        base_url="http://localhost:1234",
    )
    assert result["status"] == "error"


# ---------------------------------------------------------------------------
# pyrit_list_backend_options
# ---------------------------------------------------------------------------


@pytest.mark.unit
async def test_list_backend_options_returns_both_configs() -> None:
    """Should return both attacker and scorer backend configurations."""
    from pyrit_mcp.tools.backends import pyrit_list_backend_options

    result = await pyrit_list_backend_options()
    assert result["status"] == "success"
    data = result["data"]
    assert "attacker" in data
    assert "scorer" in data
    assert "available_backends" in data


@pytest.mark.unit
async def test_list_backend_options_redacts_keys() -> None:
    """API keys must never appear in plaintext in the response."""
    from pyrit_mcp.tools.backends import pyrit_list_backend_options

    result = await pyrit_list_backend_options()
    result_str = json.dumps(result)
    assert "sk-" not in result_str


# ---------------------------------------------------------------------------
# pyrit_test_backend_connectivity
# ---------------------------------------------------------------------------


@pytest.mark.unit
async def test_backend_connectivity_attacker_success() -> None:
    """Successful probe should return latency info."""
    from pyrit_mcp.tools.backends import pyrit_test_backend_connectivity

    mock_response = httpx.Response(
        200, json={"models": []}, request=httpx.Request("GET", "http://test")
    )
    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_response)
    mock_cm = AsyncMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_client)
    mock_cm.__aexit__ = AsyncMock(return_value=False)
    with patch("pyrit_mcp.tools.backends.httpx.AsyncClient", return_value=mock_cm):
        result = await pyrit_test_backend_connectivity(backend_role="attacker")

    assert result["status"] == "success"
    assert "latency_ms" in result["data"]


@pytest.mark.unit
async def test_backend_connectivity_invalid_role() -> None:
    """Invalid role should return an error."""
    from pyrit_mcp.tools.backends import pyrit_test_backend_connectivity

    result = await pyrit_test_backend_connectivity(backend_role="invalid")
    assert result["status"] == "error"
    assert "suggestion" in result


@pytest.mark.unit
async def test_backend_connectivity_connection_error() -> None:
    """Connection failure should return a clear error with suggestion."""
    from pyrit_mcp.tools.backends import pyrit_test_backend_connectivity

    with patch("pyrit_mcp.tools.backends.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))
        mock_client_cls.return_value = mock_client

        result = await pyrit_test_backend_connectivity(backend_role="attacker")

    assert result["status"] == "error"
    assert "suggestion" in result


# ---------------------------------------------------------------------------
# pyrit_estimate_attack_cost
# ---------------------------------------------------------------------------


@pytest.mark.unit
async def test_estimate_attack_cost_with_loaded_dataset() -> None:
    """Should return token and cost estimates for a loaded dataset."""
    from pyrit_mcp.tools.backends import pyrit_estimate_attack_cost

    # Insert a test dataset
    execute(
        "INSERT INTO datasets (dataset_id, name, category, prompt_count, prompts_json) "
        "VALUES (?, ?, ?, ?, ?)",
        ["ds-1", "test-dataset", "jailbreak", 50, json.dumps(["prompt"] * 50)],
    )

    result = await pyrit_estimate_attack_cost(dataset_name="test-dataset", backend_type="ollama")
    assert result["status"] == "success"
    data = result["data"]
    assert data["total_prompts"] == 50
    assert "estimated_input_tokens" in data
    assert "estimated_output_tokens" in data


@pytest.mark.unit
async def test_estimate_attack_cost_dataset_not_found() -> None:
    """Missing dataset should return an error."""
    from pyrit_mcp.tools.backends import pyrit_estimate_attack_cost

    result = await pyrit_estimate_attack_cost(dataset_name="nonexistent", backend_type="ollama")
    assert result["status"] == "error"
    assert "suggestion" in result


# ---------------------------------------------------------------------------
# pyrit_recommend_models
# ---------------------------------------------------------------------------


@pytest.mark.unit
async def test_recommend_models_returns_recommendations() -> None:
    """Should return tier-appropriate recommendations."""
    from pyrit_mcp.tools.backends import pyrit_recommend_models

    result = await pyrit_recommend_models(available_ram_gb=64)
    assert result["status"] == "success"
    recs = result["data"]["recommendations"]
    assert "tier_id" in recs
    assert "attacker" in recs
    assert "scorer" in recs


@pytest.mark.unit
async def test_recommend_models_with_gpu() -> None:
    """GPU flag should be reflected in the response."""
    from pyrit_mcp.tools.backends import pyrit_recommend_models

    result = await pyrit_recommend_models(available_ram_gb=64, has_gpu=True, gpu_vram_gb=24)
    assert result["status"] == "success"
    assert result["data"]["has_gpu"] is True


# ---------------------------------------------------------------------------
# pyrit_pull_ollama_model
# ---------------------------------------------------------------------------


@pytest.mark.unit
async def test_pull_ollama_model_requires_confirmation() -> None:
    """Without confirm, should return pending_confirmation."""
    from pyrit_mcp.tools.backends import pyrit_pull_ollama_model

    result = await pyrit_pull_ollama_model(model_name="dolphin-mistral")
    assert result["status"] == "pending_confirmation"


@pytest.mark.unit
async def test_pull_ollama_model_confirmed() -> None:
    """With confirm, should attempt the pull."""
    from pyrit_mcp.tools.backends import pyrit_pull_ollama_model

    mock_response = httpx.Response(
        200, json={"status": "success"}, request=httpx.Request("POST", "http://test")
    )
    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_response)
    mock_cm = AsyncMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_client)
    mock_cm.__aexit__ = AsyncMock(return_value=False)
    with patch("pyrit_mcp.tools.backends.httpx.AsyncClient", return_value=mock_cm):
        result = await pyrit_pull_ollama_model(model_name="dolphin-mistral", confirm_size_gb=True)

    assert result["status"] == "success"


@pytest.mark.unit
async def test_pull_ollama_model_connection_error() -> None:
    """Pull failure should return error with suggestion."""
    from pyrit_mcp.tools.backends import pyrit_pull_ollama_model

    with patch("pyrit_mcp.tools.backends.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(side_effect=httpx.ConnectError("refused"))
        mock_client_cls.return_value = mock_client

        result = await pyrit_pull_ollama_model(model_name="dolphin-mistral", confirm_size_gb=True)

    assert result["status"] == "error"


# ---------------------------------------------------------------------------
# pyrit_list_ollama_models
# ---------------------------------------------------------------------------


@pytest.mark.unit
async def test_list_ollama_models_success() -> None:
    """Should return parsed model list from Ollama."""
    from pyrit_mcp.tools.backends import pyrit_list_ollama_models

    mock_response = httpx.Response(
        200,
        json={
            "models": [
                {"name": "dolphin-mistral:latest", "size": 4_000_000_000},
                {"name": "nous-hermes2:latest", "size": 7_000_000_000},
            ]
        },
        request=httpx.Request("GET", "http://test"),
    )
    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_response)
    mock_cm = AsyncMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_client)
    mock_cm.__aexit__ = AsyncMock(return_value=False)
    with patch("pyrit_mcp.tools.backends.httpx.AsyncClient", return_value=mock_cm):
        result = await pyrit_list_ollama_models()

    assert result["status"] == "success"
    assert len(result["data"]["models"]) == 2


@pytest.mark.unit
async def test_list_ollama_models_connection_error() -> None:
    """Ollama not running should return error with suggestion."""
    from pyrit_mcp.tools.backends import pyrit_list_ollama_models

    with patch("pyrit_mcp.tools.backends.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(side_effect=httpx.ConnectError("refused"))
        mock_client_cls.return_value = mock_client

        result = await pyrit_list_ollama_models()

    assert result["status"] == "error"
    assert "suggestion" in result


# ---------------------------------------------------------------------------
# pyrit_benchmark_backend
# ---------------------------------------------------------------------------


@pytest.mark.unit
async def test_benchmark_backend_success() -> None:
    """Successful benchmark should return tokens/sec measurement."""
    from pyrit_mcp.tools.backends import pyrit_benchmark_backend

    mock_response = httpx.Response(
        200,
        json={
            "choices": [{"message": {"content": "Hello world this is a test response."}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 50, "total_tokens": 60},
        },
        request=httpx.Request("POST", "http://test"),
    )
    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_response)
    mock_cm = AsyncMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_client)
    mock_cm.__aexit__ = AsyncMock(return_value=False)
    with patch("pyrit_mcp.tools.backends.httpx.AsyncClient", return_value=mock_cm):
        result = await pyrit_benchmark_backend(backend_role="attacker")

    assert result["status"] == "success"
    data = result["data"]
    assert "completion_tokens" in data
    assert "elapsed_seconds" in data


@pytest.mark.unit
async def test_benchmark_backend_invalid_role() -> None:
    """Invalid role should return error."""
    from pyrit_mcp.tools.backends import pyrit_benchmark_backend

    result = await pyrit_benchmark_backend(backend_role="invalid")
    assert result["status"] == "error"
    assert "suggestion" in result


@pytest.mark.unit
async def test_benchmark_backend_connection_error() -> None:
    """Connection failure should return error with suggestion."""
    from pyrit_mcp.tools.backends import pyrit_benchmark_backend

    with patch("pyrit_mcp.tools.backends.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(side_effect=httpx.ConnectError("refused"))
        mock_client_cls.return_value = mock_client

        result = await pyrit_benchmark_backend(backend_role="attacker")

    assert result["status"] == "error"
