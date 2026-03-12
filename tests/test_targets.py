"""
Tests for pyrit_mcp target management tools (Domain 1).

Tests cover all 6 target tools:
  - pyrit_configure_http_target
  - pyrit_configure_openai_target
  - pyrit_configure_azure_target
  - pyrit_list_targets
  - pyrit_remove_target
  - pyrit_test_target_connectivity (mocked HTTP)
"""

from __future__ import annotations

import json

import pytest

from pyrit_mcp.tools.targets import (
    pyrit_configure_azure_target,
    pyrit_configure_http_target,
    pyrit_configure_openai_target,
    pyrit_list_targets,
    pyrit_remove_target,
    pyrit_test_target_connectivity,
)
from pyrit_mcp.utils.db import execute, fetchone

# ---------------------------------------------------------------------------
# pyrit_configure_http_target
# ---------------------------------------------------------------------------


@pytest.mark.unit
async def test_configure_http_target_success() -> None:
    result = await pyrit_configure_http_target(url="http://example.com/api")
    assert result["status"] == "success"
    data = result["data"]
    assert "target_id" in data
    assert data["target_type"] == "http"
    assert len(data["target_id"]) == 36  # UUID format


@pytest.mark.unit
async def test_configure_http_target_persists_to_db() -> None:
    result = await pyrit_configure_http_target(url="http://example.com/api")
    target_id = result["data"]["target_id"]

    row = fetchone("SELECT target_type, config_json FROM targets WHERE target_id = ?", [target_id])
    assert row is not None
    assert row[0] == "http"
    config = json.loads(row[1])
    assert config["url"] == "http://example.com/api"


@pytest.mark.unit
async def test_configure_http_target_invalid_url() -> None:
    result = await pyrit_configure_http_target(url="not-a-url")
    assert result["status"] == "error"
    assert "suggestion" in result


@pytest.mark.unit
async def test_configure_http_target_with_headers() -> None:
    result = await pyrit_configure_http_target(
        url="http://example.com/api",
        headers='{"Authorization": "Bearer tok", "X-Custom": "value"}',
    )
    assert result["status"] == "success"
    # Verify headers stored correctly
    target_id = result["data"]["target_id"]
    row = fetchone("SELECT config_json FROM targets WHERE target_id = ?", [target_id])
    config = json.loads(row[0])
    assert config["headers"]["X-Custom"] == "value"


@pytest.mark.unit
async def test_configure_http_target_invalid_headers_json() -> None:
    result = await pyrit_configure_http_target(
        url="http://example.com/api",
        headers="not valid json",
    )
    assert result["status"] == "error"


@pytest.mark.unit
async def test_configure_http_target_with_request_template() -> None:
    """Verify custom request_template is stored in config."""
    template = '{"input": "{prompt}", "context": "test"}'
    result = await pyrit_configure_http_target(
        url="http://example.com/api",
        request_template=template,
    )
    assert result["status"] == "success"
    target_id = result["data"]["target_id"]
    row = fetchone("SELECT config_json FROM targets WHERE target_id = ?", [target_id])
    config = json.loads(row[0])
    assert config["request_template"] == template


@pytest.mark.unit
async def test_configure_http_target_with_response_path() -> None:
    """Verify response_path is stored in config."""
    result = await pyrit_configure_http_target(
        url="http://example.com/api",
        response_path="choices.0.message.content",
    )
    assert result["status"] == "success"
    target_id = result["data"]["target_id"]
    row = fetchone("SELECT config_json FROM targets WHERE target_id = ?", [target_id])
    config = json.loads(row[0])
    assert config["response_path"] == "choices.0.message.content"


@pytest.mark.unit
async def test_configure_http_target_with_api_key_env() -> None:
    """Verify api_key_env name is stored (not the value)."""
    result = await pyrit_configure_http_target(
        url="http://example.com/api",
        api_key_env="MY_HTTP_KEY",
    )
    assert result["status"] == "success"
    target_id = result["data"]["target_id"]
    row = fetchone("SELECT config_json FROM targets WHERE target_id = ?", [target_id])
    config = json.loads(row[0])
    assert config["api_key_env"] == "MY_HTTP_KEY"


@pytest.mark.unit
async def test_configure_http_target_defaults() -> None:
    """Verify default request_template, response_path, api_key_env when not provided."""
    result = await pyrit_configure_http_target(url="http://example.com/api")
    target_id = result["data"]["target_id"]
    row = fetchone("SELECT config_json FROM targets WHERE target_id = ?", [target_id])
    config = json.loads(row[0])
    assert config["request_template"] == '{"message": "{prompt}"}'
    assert config["response_path"] == ""
    assert config["api_key_env"] == ""


@pytest.mark.unit
async def test_configure_http_target_https_url() -> None:
    """HTTPS URLs should be accepted."""
    result = await pyrit_configure_http_target(url="https://secure.example.com/api")
    assert result["status"] == "success"
    assert result["data"]["url"] == "https://secure.example.com/api"


# ---------------------------------------------------------------------------
# pyrit_configure_openai_target
# ---------------------------------------------------------------------------


@pytest.mark.unit
async def test_configure_openai_target_success() -> None:
    result = await pyrit_configure_openai_target(
        api_base="http://localhost:11434",
        model="dolphin-mistral",
    )
    assert result["status"] == "success"
    data = result["data"]
    assert data["target_type"] == "openai"
    assert data["model"] == "dolphin-mistral"


@pytest.mark.unit
async def test_configure_openai_target_persists_config() -> None:
    result = await pyrit_configure_openai_target(
        api_base="http://localhost:11434",
        model="test-model",
        system_prompt="You are a helpful assistant.",
        temperature=0.5,
    )
    target_id = result["data"]["target_id"]
    row = fetchone("SELECT config_json FROM targets WHERE target_id = ?", [target_id])
    config = json.loads(row[0])
    assert config["model"] == "test-model"
    assert config["system_prompt"] == "You are a helpful assistant."
    assert config["temperature"] == 0.5


@pytest.mark.unit
async def test_configure_openai_target_api_key_env_name_stored_not_value(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify that only the env var NAME is stored, never the actual key value."""
    monkeypatch.setenv("MY_SECRET_KEY", "sk-super-secret-value")

    result = await pyrit_configure_openai_target(
        api_base="http://localhost:11434",
        model="test-model",
        api_key_env="MY_SECRET_KEY",
    )
    target_id = result["data"]["target_id"]
    row = fetchone("SELECT config_json FROM targets WHERE target_id = ?", [target_id])
    config = json.loads(row[0])

    # The env var NAME should be stored
    assert config["api_key_env"] == "MY_SECRET_KEY"
    # The actual key VALUE must NEVER be in the stored config
    assert "sk-super-secret-value" not in json.dumps(config)


@pytest.mark.unit
async def test_configure_openai_target_invalid_url() -> None:
    result = await pyrit_configure_openai_target(
        api_base="localhost:11434",  # missing scheme
        model="test-model",
    )
    assert result["status"] == "error"
    assert "http" in result["error"].lower() or "url" in result["error"].lower()


@pytest.mark.unit
async def test_configure_openai_target_trailing_slash_stripped() -> None:
    """api_base trailing slash should be stripped before storage."""
    result = await pyrit_configure_openai_target(
        api_base="http://localhost:11434/",
        model="test-model",
    )
    assert result["status"] == "success"
    target_id = result["data"]["target_id"]
    row = fetchone("SELECT config_json FROM targets WHERE target_id = ?", [target_id])
    config = json.loads(row[0])
    assert config["api_base"] == "http://localhost:11434"


@pytest.mark.unit
async def test_configure_openai_target_max_tokens() -> None:
    """Verify custom max_tokens is stored."""
    result = await pyrit_configure_openai_target(
        api_base="http://localhost:11434",
        model="test-model",
        max_tokens=2048,
    )
    assert result["status"] == "success"
    target_id = result["data"]["target_id"]
    row = fetchone("SELECT config_json FROM targets WHERE target_id = ?", [target_id])
    config = json.loads(row[0])
    assert config["max_tokens"] == 2048


@pytest.mark.unit
async def test_configure_openai_target_default_values() -> None:
    """Verify default temperature, max_tokens, system_prompt, api_key_env."""
    result = await pyrit_configure_openai_target(
        api_base="http://localhost:11434",
        model="test-model",
    )
    target_id = result["data"]["target_id"]
    row = fetchone("SELECT config_json FROM targets WHERE target_id = ?", [target_id])
    config = json.loads(row[0])
    assert config["temperature"] == 0.7
    assert config["max_tokens"] == 1024
    assert config["system_prompt"] == ""
    assert config["api_key_env"] == ""


# ---------------------------------------------------------------------------
# pyrit_configure_azure_target
# ---------------------------------------------------------------------------


@pytest.mark.unit
async def test_configure_azure_target_missing_endpoint() -> None:
    """Should fail with clear error when AZURE_OPENAI_ENDPOINT is not set."""
    result = await pyrit_configure_azure_target(
        deployment_name="my-deployment",
        endpoint_env="AZURE_OPENAI_ENDPOINT_NONEXISTENT",
    )
    assert result["status"] == "error"
    assert "AZURE_OPENAI_ENDPOINT_NONEXISTENT" in result["error"]


@pytest.mark.unit
async def test_configure_azure_target_success(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://my-resource.openai.azure.com")
    result = await pyrit_configure_azure_target(deployment_name="gpt-4o-deployment")
    assert result["status"] == "success"
    assert result["data"]["target_type"] == "azure"
    assert result["data"]["deployment_name"] == "gpt-4o-deployment"


@pytest.mark.unit
async def test_configure_azure_target_persists_full_config(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify all Azure config fields are persisted correctly."""
    monkeypatch.setenv("MY_AZURE_ENDPOINT", "https://my.openai.azure.com")
    result = await pyrit_configure_azure_target(
        deployment_name="gpt-4o",
        endpoint_env="MY_AZURE_ENDPOINT",
        api_key_env="MY_AZURE_KEY",
        api_version="2024-06-01",
        system_prompt="You are a test bot.",
        content_filter_override=True,
    )
    assert result["status"] == "success"
    target_id = result["data"]["target_id"]
    row = fetchone("SELECT config_json FROM targets WHERE target_id = ?", [target_id])
    config = json.loads(row[0])
    assert config["deployment_name"] == "gpt-4o"
    assert config["endpoint_env"] == "MY_AZURE_ENDPOINT"
    assert config["api_key_env"] == "MY_AZURE_KEY"
    assert config["api_version"] == "2024-06-01"
    assert config["system_prompt"] == "You are a test bot."
    assert config["content_filter_override"] is True


@pytest.mark.unit
async def test_configure_azure_target_default_env_vars(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify default endpoint_env and api_key_env values."""
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://default.openai.azure.com")
    result = await pyrit_configure_azure_target(deployment_name="my-deploy")
    assert result["status"] == "success"
    target_id = result["data"]["target_id"]
    row = fetchone("SELECT config_json FROM targets WHERE target_id = ?", [target_id])
    config = json.loads(row[0])
    assert config["endpoint_env"] == "AZURE_OPENAI_ENDPOINT"
    assert config["api_key_env"] == "AZURE_OPENAI_API_KEY"
    assert config["content_filter_override"] is False


@pytest.mark.unit
async def test_configure_azure_target_no_system_prompt(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify system_prompt defaults to empty string when not provided."""
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://res.openai.azure.com")
    result = await pyrit_configure_azure_target(deployment_name="deploy")
    target_id = result["data"]["target_id"]
    row = fetchone("SELECT config_json FROM targets WHERE target_id = ?", [target_id])
    config = json.loads(row[0])
    assert config["system_prompt"] == ""


# ---------------------------------------------------------------------------
# pyrit_list_targets
# ---------------------------------------------------------------------------


@pytest.mark.unit
async def test_list_targets_empty() -> None:
    result = await pyrit_list_targets()
    assert result["status"] == "success"
    assert result["data"]["targets"] == []
    assert result["data"]["count"] == 0


@pytest.mark.unit
async def test_list_targets_returns_all(sample_target_id: str) -> None:
    # sample_target_id fixture inserts one target
    result = await pyrit_list_targets()
    assert result["status"] == "success"
    assert result["data"]["count"] == 1
    targets = result["data"]["targets"]
    assert targets[0]["target_id"] == sample_target_id
    assert targets[0]["target_type"] == "openai"


@pytest.mark.unit
async def test_list_targets_multiple() -> None:
    await pyrit_configure_openai_target(api_base="http://localhost:11434", model="model-a")
    await pyrit_configure_http_target(url="http://example.com/api")
    result = await pyrit_list_targets()
    assert result["data"]["count"] == 2


@pytest.mark.unit
async def test_list_targets_never_exposes_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SECRET_KEY", "sk-should-never-appear")
    await pyrit_configure_openai_target(
        api_base="http://localhost:11434",
        model="test",
        api_key_env="SECRET_KEY",
    )
    result = await pyrit_list_targets()
    response_str = json.dumps(result)
    assert "sk-should-never-appear" not in response_str


@pytest.mark.unit
async def test_list_targets_strips_resolved_key() -> None:
    """Verify _resolved_key is removed from listed target configs."""
    # Insert a target with _resolved_key in config_json directly
    import uuid

    target_id = str(uuid.uuid4())
    config = {
        "api_base": "http://localhost:11434",
        "model": "test",
        "api_key_env": "KEY",
        "_resolved_key": "secret-value-should-not-appear",
    }
    execute(
        "INSERT INTO targets (target_id, target_type, config_json) VALUES (?, ?, ?)",
        [target_id, "openai", json.dumps(config)],
    )
    result = await pyrit_list_targets()
    listed = result["data"]["targets"][0]
    assert "_resolved_key" not in listed["config"]
    assert "secret-value-should-not-appear" not in json.dumps(listed)


@pytest.mark.unit
async def test_list_targets_includes_created_at(sample_target_id: str) -> None:
    """Each listed target should have a created_at field."""
    result = await pyrit_list_targets()
    targets = result["data"]["targets"]
    assert len(targets) == 1
    assert "created_at" in targets[0]


# ---------------------------------------------------------------------------
# pyrit_remove_target
# ---------------------------------------------------------------------------


@pytest.mark.unit
async def test_remove_target_requires_confirm(sample_target_id: str) -> None:
    result = await pyrit_remove_target(target_id=sample_target_id, confirm=False)
    assert result["status"] == "pending_confirmation"
    # Target should still exist in DB
    row = fetchone("SELECT target_id FROM targets WHERE target_id = ?", [sample_target_id])
    assert row is not None


@pytest.mark.unit
async def test_remove_target_with_confirm(sample_target_id: str) -> None:
    result = await pyrit_remove_target(target_id=sample_target_id, confirm=True)
    assert result["status"] == "success"
    assert result["data"]["deleted"] is True
    # Target should be gone from DB
    row = fetchone("SELECT target_id FROM targets WHERE target_id = ?", [sample_target_id])
    assert row is None


@pytest.mark.unit
async def test_remove_target_not_found() -> None:
    result = await pyrit_remove_target(target_id="nonexistent-id", confirm=True)
    assert result["status"] == "error"
    assert "suggestion" in result


@pytest.mark.unit
async def test_remove_target_pending_message_contains_type(sample_target_id: str) -> None:
    """The pending confirmation message should mention the target type."""
    result = await pyrit_remove_target(target_id=sample_target_id, confirm=False)
    assert result["status"] == "pending_confirmation"
    assert "openai" in result["message"]


@pytest.mark.unit
async def test_remove_target_success_returns_target_id(sample_target_id: str) -> None:
    """Verify the success response includes the deleted target_id."""
    result = await pyrit_remove_target(target_id=sample_target_id, confirm=True)
    assert result["data"]["target_id"] == sample_target_id
    assert "message" in result["data"]


# ---------------------------------------------------------------------------
# pyrit_test_target_connectivity (mocked)
# ---------------------------------------------------------------------------


@pytest.mark.unit
async def test_test_connectivity_target_not_found() -> None:
    result = await pyrit_test_target_connectivity(target_id="nonexistent")
    assert result["status"] == "error"
    assert "suggestion" in result


@pytest.mark.unit
async def test_test_connectivity_success(
    sample_target_id: str,
) -> None:
    """Mock the HTTP probe to avoid real network calls."""
    from unittest.mock import AsyncMock, patch

    with patch(
        "pyrit_mcp.tools.targets._probe_openai_target",
        new_callable=AsyncMock,
        return_value="CONNECTED",
    ):
        result = await pyrit_test_target_connectivity(target_id=sample_target_id)
    assert result["status"] == "success"
    assert result["data"]["reachable"] is True


@pytest.mark.unit
async def test_test_connectivity_empty_response(sample_target_id: str) -> None:
    """Empty probe response should show '(empty response)' in preview."""
    from unittest.mock import AsyncMock, patch

    with patch(
        "pyrit_mcp.tools.targets._probe_openai_target",
        new_callable=AsyncMock,
        return_value="",
    ):
        result = await pyrit_test_target_connectivity(target_id=sample_target_id)
    assert result["status"] == "success"
    assert result["data"]["reachable"] is True
    assert result["data"]["response_preview"] == "(empty response)"


@pytest.mark.unit
async def test_test_connectivity_response_truncated(sample_target_id: str) -> None:
    """Long probe responses should be truncated to 200 chars."""
    from unittest.mock import AsyncMock, patch

    long_response = "A" * 500
    with patch(
        "pyrit_mcp.tools.targets._probe_openai_target",
        new_callable=AsyncMock,
        return_value=long_response,
    ):
        result = await pyrit_test_target_connectivity(target_id=sample_target_id)
    assert result["status"] == "success"
    assert len(result["data"]["response_preview"]) == 200


@pytest.mark.unit
async def test_test_connectivity_connect_error(sample_target_id: str) -> None:
    """ConnectError should return a structured error response."""
    from unittest.mock import AsyncMock, patch

    import httpx

    with patch(
        "pyrit_mcp.tools.targets._probe_openai_target",
        new_callable=AsyncMock,
        side_effect=httpx.ConnectError("Connection refused"),
    ):
        result = await pyrit_test_target_connectivity(target_id=sample_target_id)
    assert result["status"] == "error"
    assert "connect" in result["error"].lower() or "Connect" in result["error"]
    assert "suggestion" in result


@pytest.mark.unit
async def test_test_connectivity_timeout_error(sample_target_id: str) -> None:
    """TimeoutException should return a structured error about timeout."""
    from unittest.mock import AsyncMock, patch

    import httpx

    with patch(
        "pyrit_mcp.tools.targets._probe_openai_target",
        new_callable=AsyncMock,
        side_effect=httpx.TimeoutException("Request timed out"),
    ):
        result = await pyrit_test_target_connectivity(target_id=sample_target_id)
    assert result["status"] == "error"
    assert "timed out" in result["error"].lower()
    assert "suggestion" in result


@pytest.mark.unit
async def test_test_connectivity_generic_exception(sample_target_id: str) -> None:
    """Generic exceptions should return a structured error."""
    from unittest.mock import AsyncMock, patch

    with patch(
        "pyrit_mcp.tools.targets._probe_openai_target",
        new_callable=AsyncMock,
        side_effect=RuntimeError("Something unexpected"),
    ):
        result = await pyrit_test_target_connectivity(target_id=sample_target_id)
    assert result["status"] == "error"
    assert "Something unexpected" in result["error"]
    assert "suggestion" in result


@pytest.mark.unit
async def test_test_connectivity_http_target() -> None:
    """Connectivity test on an HTTP target should invoke _probe_http_target."""
    from unittest.mock import AsyncMock, patch

    result = await pyrit_configure_http_target(url="http://example.com/api")
    target_id = result["data"]["target_id"]

    with patch(
        "pyrit_mcp.tools.targets._probe_http_target",
        new_callable=AsyncMock,
        return_value="OK",
    ) as mock_probe:
        result = await pyrit_test_target_connectivity(target_id=target_id)
    assert result["status"] == "success"
    assert result["data"]["target_type"] == "http"
    mock_probe.assert_awaited_once()


@pytest.mark.unit
async def test_test_connectivity_azure_target(monkeypatch: pytest.MonkeyPatch) -> None:
    """Connectivity test on an Azure target should invoke _probe_azure_target."""
    from unittest.mock import AsyncMock, patch

    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://res.openai.azure.com")
    result = await pyrit_configure_azure_target(deployment_name="gpt-4o")
    target_id = result["data"]["target_id"]

    with patch(
        "pyrit_mcp.tools.targets._probe_azure_target",
        new_callable=AsyncMock,
        return_value="Hello!",
    ) as mock_probe:
        result = await pyrit_test_target_connectivity(target_id=target_id)
    assert result["status"] == "success"
    assert result["data"]["target_type"] == "azure"
    mock_probe.assert_awaited_once()


@pytest.mark.unit
async def test_test_connectivity_unknown_target_type() -> None:
    """Unknown target type should return an error about unimplemented probe."""
    import uuid

    target_id = str(uuid.uuid4())
    execute(
        "INSERT INTO targets (target_id, target_type, config_json) VALUES (?, ?, ?)",
        [target_id, "custom_unknown", json.dumps({"url": "http://example.com"})],
    )
    result = await pyrit_test_target_connectivity(target_id=target_id)
    assert result["status"] == "error"
    assert "not implemented" in result["error"].lower()


@pytest.mark.unit
async def test_test_connectivity_custom_probe_prompt(sample_target_id: str) -> None:
    """Verify custom probe_prompt is passed to the probe function."""
    from unittest.mock import AsyncMock, patch

    with patch(
        "pyrit_mcp.tools.targets._probe_openai_target",
        new_callable=AsyncMock,
        return_value="PONG",
    ) as mock_probe:
        result = await pyrit_test_target_connectivity(
            target_id=sample_target_id,
            probe_prompt="PING",
        )
    assert result["status"] == "success"
    # Check that custom prompt was forwarded
    call_args = mock_probe.call_args
    assert call_args[0][1] == "PING" or call_args[1].get("prompt") == "PING"


# ---------------------------------------------------------------------------
# _probe_openai_target (via mocked httpx)
# ---------------------------------------------------------------------------


@pytest.mark.unit
async def test_probe_openai_target_with_system_prompt() -> None:
    """_probe_openai_target should include system_prompt in messages when set."""
    from unittest.mock import AsyncMock, MagicMock, patch

    from pyrit_mcp.tools.targets import _probe_openai_target

    mock_response = MagicMock()
    mock_response.json.return_value = {
        "choices": [{"message": {"content": "Hello!"}}]
    }
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_response)
    mock_cm = AsyncMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_client)
    mock_cm.__aexit__ = AsyncMock(return_value=False)

    config = {
        "api_base": "http://localhost:11434",
        "model": "test-model",
        "api_key_env": "",
        "system_prompt": "You are a test bot.",
    }
    with patch("pyrit_mcp.tools.targets.httpx.AsyncClient", return_value=mock_cm):
        result = await _probe_openai_target(config, "Hi")

    assert result == "Hello!"
    # Verify system message was included
    call_args = mock_client.post.call_args
    messages = call_args[1]["json"]["messages"]
    assert messages[0]["role"] == "system"
    assert messages[0]["content"] == "You are a test bot."
    assert messages[1]["role"] == "user"


@pytest.mark.unit
async def test_probe_openai_target_no_system_prompt() -> None:
    """_probe_openai_target without system_prompt should only send user message."""
    from unittest.mock import AsyncMock, MagicMock, patch

    from pyrit_mcp.tools.targets import _probe_openai_target

    mock_response = MagicMock()
    mock_response.json.return_value = {
        "choices": [{"message": {"content": "OK"}}]
    }
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_response)
    mock_cm = AsyncMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_client)
    mock_cm.__aexit__ = AsyncMock(return_value=False)

    config = {
        "api_base": "http://localhost:11434",
        "model": "test-model",
        "api_key_env": "",
        "system_prompt": "",
    }
    with patch("pyrit_mcp.tools.targets.httpx.AsyncClient", return_value=mock_cm):
        result = await _probe_openai_target(config, "Hi")

    assert result == "OK"
    call_args = mock_client.post.call_args
    messages = call_args[1]["json"]["messages"]
    assert len(messages) == 1
    assert messages[0]["role"] == "user"


@pytest.mark.unit
async def test_probe_openai_target_uses_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """_probe_openai_target should resolve api_key_env from environment."""
    from unittest.mock import AsyncMock, MagicMock, patch

    from pyrit_mcp.tools.targets import _probe_openai_target

    monkeypatch.setenv("TEST_OPENAI_KEY", "sk-test-key-12345")

    mock_response = MagicMock()
    mock_response.json.return_value = {
        "choices": [{"message": {"content": "Hi"}}]
    }
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_response)
    mock_cm = AsyncMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_client)
    mock_cm.__aexit__ = AsyncMock(return_value=False)

    config = {
        "api_base": "http://localhost:11434",
        "model": "test-model",
        "api_key_env": "TEST_OPENAI_KEY",
        "system_prompt": "",
    }
    with patch("pyrit_mcp.tools.targets.httpx.AsyncClient", return_value=mock_cm):
        await _probe_openai_target(config, "test")

    call_args = mock_client.post.call_args
    headers = call_args[1]["headers"]
    assert headers["Authorization"] == "Bearer sk-test-key-12345"


# ---------------------------------------------------------------------------
# _probe_http_target (via mocked httpx)
# ---------------------------------------------------------------------------


@pytest.mark.unit
async def test_probe_http_target_basic() -> None:
    """_probe_http_target should POST to the configured URL."""
    from unittest.mock import AsyncMock, MagicMock, patch

    from pyrit_mcp.tools.targets import _probe_http_target

    mock_response = MagicMock()
    mock_response.text = "response body"
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_response)
    mock_cm = AsyncMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_client)
    mock_cm.__aexit__ = AsyncMock(return_value=False)

    config = {
        "url": "http://example.com/api",
        "headers": {"Content-Type": "application/json"},
        "request_template": '{"message": "{prompt}"}',
        "api_key_env": "",
    }
    with patch("pyrit_mcp.tools.targets.httpx.AsyncClient", return_value=mock_cm):
        result = await _probe_http_target(config, "test prompt")

    assert result == "response body"
    call_args = mock_client.post.call_args
    assert call_args[0][0] == "http://example.com/api"
    body = call_args[1]["json"]
    assert body["message"] == "test prompt"


@pytest.mark.unit
async def test_probe_http_target_with_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """_probe_http_target should add Bearer token when api_key_env is set."""
    from unittest.mock import AsyncMock, MagicMock, patch

    from pyrit_mcp.tools.targets import _probe_http_target

    monkeypatch.setenv("HTTP_API_KEY", "bearer-token-123")

    mock_response = MagicMock()
    mock_response.text = "OK"
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_response)
    mock_cm = AsyncMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_client)
    mock_cm.__aexit__ = AsyncMock(return_value=False)

    config = {
        "url": "http://example.com/api",
        "headers": {},
        "request_template": '{"msg": "{prompt}"}',
        "api_key_env": "HTTP_API_KEY",
    }
    with patch("pyrit_mcp.tools.targets.httpx.AsyncClient", return_value=mock_cm):
        await _probe_http_target(config, "test")

    call_args = mock_client.post.call_args
    headers = call_args[1]["headers"]
    assert headers["Authorization"] == "Bearer bearer-token-123"


@pytest.mark.unit
async def test_probe_http_target_invalid_template_fallback() -> None:
    """Invalid JSON after template substitution should fall back to default body."""
    from unittest.mock import AsyncMock, MagicMock, patch

    from pyrit_mcp.tools.targets import _probe_http_target

    mock_response = MagicMock()
    mock_response.text = "fallback OK"
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_response)
    mock_cm = AsyncMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_client)
    mock_cm.__aexit__ = AsyncMock(return_value=False)

    config = {
        "url": "http://example.com/api",
        "headers": {},
        "request_template": "not valid json {prompt}",
        "api_key_env": "",
    }
    with patch("pyrit_mcp.tools.targets.httpx.AsyncClient", return_value=mock_cm):
        result = await _probe_http_target(config, "hello")

    assert result == "fallback OK"
    call_args = mock_client.post.call_args
    body = call_args[1]["json"]
    assert body == {"message": "hello"}


@pytest.mark.unit
async def test_probe_http_target_response_truncated() -> None:
    """_probe_http_target should truncate response text to 200 chars."""
    from unittest.mock import AsyncMock, MagicMock, patch

    from pyrit_mcp.tools.targets import _probe_http_target

    mock_response = MagicMock()
    mock_response.text = "X" * 500
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_response)
    mock_cm = AsyncMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_client)
    mock_cm.__aexit__ = AsyncMock(return_value=False)

    config = {
        "url": "http://example.com/api",
        "headers": {},
        "request_template": '{"m": "{prompt}"}',
        "api_key_env": "",
    }
    with patch("pyrit_mcp.tools.targets.httpx.AsyncClient", return_value=mock_cm):
        result = await _probe_http_target(config, "test")

    assert len(result) == 200


# ---------------------------------------------------------------------------
# _probe_azure_target (via mocked httpx)
# ---------------------------------------------------------------------------


@pytest.mark.unit
async def test_probe_azure_target(monkeypatch: pytest.MonkeyPatch) -> None:
    """_probe_azure_target should POST to the Azure completions endpoint."""
    from unittest.mock import AsyncMock, MagicMock, patch

    from pyrit_mcp.tools.targets import _probe_azure_target

    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://res.openai.azure.com")
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "az-key-123")

    mock_response = MagicMock()
    mock_response.json.return_value = {
        "choices": [{"message": {"content": "Azure says hi"}}]
    }
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_response)
    mock_cm = AsyncMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_client)
    mock_cm.__aexit__ = AsyncMock(return_value=False)

    config = {
        "deployment_name": "gpt-4o",
        "endpoint_env": "AZURE_OPENAI_ENDPOINT",
        "api_key_env": "AZURE_OPENAI_API_KEY",
        "api_version": "2024-02-01",
    }
    with patch("pyrit_mcp.tools.targets.httpx.AsyncClient", return_value=mock_cm):
        result = await _probe_azure_target(config, "Hello")

    assert result == "Azure says hi"
    call_args = mock_client.post.call_args
    url = call_args[0][0]
    assert "gpt-4o" in url
    assert "api-version=2024-02-01" in url
    assert call_args[1]["headers"]["api-key"] == "az-key-123"


# ---------------------------------------------------------------------------
# _row_to_target helper
# ---------------------------------------------------------------------------


@pytest.mark.unit
async def test_row_to_target_with_dict_config() -> None:
    """_row_to_target should handle config_json as a dict (non-string)."""
    from pyrit_mcp.tools.targets import _row_to_target

    config_dict = {"model": "test", "api_key_env": "KEY"}
    row = ("id-123", "openai", config_dict, "2025-01-01T00:00:00")
    result = _row_to_target(row)
    assert result["target_id"] == "id-123"
    assert result["target_type"] == "openai"
    assert result["config"]["model"] == "test"


@pytest.mark.unit
async def test_row_to_target_strips_resolved_key() -> None:
    """_row_to_target should remove _resolved_key from config output."""
    from pyrit_mcp.tools.targets import _row_to_target

    config_str = json.dumps({
        "model": "test",
        "_resolved_key": "should-be-removed",
    })
    row = ("id-456", "openai", config_str, "2025-01-01T00:00:00")
    result = _row_to_target(row)
    assert "_resolved_key" not in result["config"]
    assert result["config"]["model"] == "test"


@pytest.mark.unit
async def test_row_to_target_created_at_as_string() -> None:
    """_row_to_target should convert created_at to string."""
    from pyrit_mcp.tools.targets import _row_to_target

    row = ("id-789", "http", '{"url": "http://x.com"}', 12345)
    result = _row_to_target(row)
    assert result["created_at"] == "12345"
