"""
pyrit_mcp.config — Configuration management for the PyRIT MCP server.

Loads environment variables with a two-layer priority system:
  1. .env.detected  (lower priority — auto-detected hardware values)
  2. .env            (higher priority — explicit user overrides)

All application code should import from this module rather than reading
os.environ directly, so configuration is validated in one place at startup.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from dotenv import load_dotenv


def _load_env_files() -> None:
    """Load environment files in priority order.

    .env.detected is loaded first (lower priority — base auto-detected values).
    .env is loaded second (higher priority — user overrides win).
    """
    detected = Path(".env.detected")
    if detected.exists():
        load_dotenv(detected, override=False)
    load_dotenv(override=True)


_load_env_files()


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class BackendType(str, Enum):
    """Supported LLM backend providers."""

    OLLAMA = "ollama"
    LLAMACPP = "llamacpp"
    AZURE = "azure"
    OPENAI = "openai"
    GROQ = "groq"
    LMSTUDIO = "lmstudio"
    SUBSTRING = "substring"
    CLASSIFIER = "classifier"


# ---------------------------------------------------------------------------
# Backend configuration dataclasses
# ---------------------------------------------------------------------------


@dataclass
class AttackerBackendConfig:
    """Configuration for the attacker LLM backend.

    The attacker generates adversarial prompts, so it MUST be uncensored.
    Recommended backends: Ollama or llama.cpp with an uncensored model.
    The api_key_env field holds the NAME of the env var containing the key,
    never the key value itself.
    """

    backend_type: BackendType
    base_url: str
    model: str
    temperature: float = 1.0
    max_tokens: int = 2048
    timeout_seconds: int = 60
    quantization: str = ""
    api_key_env: str = ""

    @property
    def api_key(self) -> str:
        """Resolve the actual API key from the environment at call time.

        The key is never stored in this object — it is read fresh each call
        so that secret rotation does not require a server restart.
        """
        if not self.api_key_env:
            return ""
        return os.environ.get(self.api_key_env, "")


@dataclass
class ScorerBackendConfig:
    """Configuration for the scorer LLM backend.

    The scorer evaluates responses for harmful content, so it can be
    safety-filtered. Temperature is 0.0 for deterministic scoring.
    """

    backend_type: BackendType
    base_url: str
    model: str
    temperature: float = 0.0
    scoring_scale: str = "likert_1_10"
    quantization: str = ""
    api_key_env: str = ""

    @property
    def api_key(self) -> str:
        """Resolve the actual API key from the environment at call time."""
        if not self.api_key_env:
            return ""
        return os.environ.get(self.api_key_env, "")


# ---------------------------------------------------------------------------
# Server configuration dataclass
# ---------------------------------------------------------------------------


@dataclass
class ServerConfig:
    """Top-level server configuration loaded from environment variables."""

    db_path: str = field(default_factory=lambda: os.environ.get("PYRIT_DB_PATH", "/data/pyrit.db"))
    log_level: str = field(default_factory=lambda: os.environ.get("PYRIT_LOG_LEVEL", "INFO"))
    default_rps: float = field(
        default_factory=lambda: float(os.environ.get("PYRIT_DEFAULT_RPS", "2"))
    )
    default_max_requests: int = field(
        default_factory=lambda: int(os.environ.get("PYRIT_DEFAULT_MAX_REQUESTS", "100"))
    )
    sandbox_mode: bool = field(
        default_factory=lambda: os.environ.get("PYRIT_SANDBOX_MODE", "false").lower() == "true"
    )
    attacker: AttackerBackendConfig = field(init=False)
    scorer: ScorerBackendConfig = field(init=False)

    def __post_init__(self) -> None:
        """Construct nested backend configs from environment variables."""
        self.attacker = AttackerBackendConfig(
            backend_type=BackendType(os.environ.get("ATTACKER_BACKEND", "ollama").lower()),
            base_url=os.environ.get("ATTACKER_BASE_URL", "http://ollama:11434"),
            model=os.environ.get("ATTACKER_MODEL", "dolphin-mistral"),
            temperature=float(os.environ.get("ATTACKER_TEMPERATURE", "1.0")),
            max_tokens=int(os.environ.get("ATTACKER_MAX_TOKENS", "2048")),
            timeout_seconds=int(os.environ.get("ATTACKER_TIMEOUT", "60")),
            quantization=os.environ.get("ATTACKER_QUANTIZATION", ""),
            api_key_env=os.environ.get("ATTACKER_API_KEY_ENV", ""),
        )
        self.scorer = ScorerBackendConfig(
            backend_type=BackendType(os.environ.get("SCORER_BACKEND", "substring").lower()),
            base_url=os.environ.get("SCORER_BASE_URL", ""),
            model=os.environ.get("SCORER_MODEL", ""),
            temperature=float(os.environ.get("SCORER_TEMPERATURE", "0.0")),
            quantization=os.environ.get("SCORER_QUANTIZATION", ""),
            api_key_env=os.environ.get("SCORER_API_KEY_ENV", ""),
        )


# ---------------------------------------------------------------------------
# Config validation
# ---------------------------------------------------------------------------

_REQUIRED_VARS: dict[str, list[str]] = {
    "base": ["ATTACKER_BACKEND", "ATTACKER_BASE_URL", "ATTACKER_MODEL"],
    "openai_scorer": ["SCORER_BASE_URL", "SCORER_MODEL"],
    "azure": [
        "AZURE_OPENAI_ENDPOINT",
        "AZURE_OPENAI_API_KEY",
        "AZURE_API_VERSION",
    ],
}


def validate_config(config: ServerConfig) -> list[str]:
    """Validate configuration and return a list of error strings.

    Returns an empty list if configuration is valid. Callers should
    fail fast (sys.exit) if any errors are returned.
    """
    errors: list[str] = []

    # Attacker must have base_url and model
    if not config.attacker.base_url:
        errors.append("ATTACKER_BASE_URL is required but not set.")
    if not config.attacker.model:
        errors.append("ATTACKER_MODEL is required but not set.")

    # If scorer is an LLM backend, it needs a base_url and model
    if config.scorer.backend_type not in (
        BackendType.SUBSTRING,
        BackendType.CLASSIFIER,
    ):
        if not config.scorer.base_url:
            errors.append(
                f"SCORER_BASE_URL is required for SCORER_BACKEND={config.scorer.backend_type.value}"
            )
        if not config.scorer.model:
            errors.append(
                f"SCORER_MODEL is required for SCORER_BACKEND={config.scorer.backend_type.value}"
            )

    # Azure requires endpoint and API key env
    if config.attacker.backend_type == BackendType.AZURE:
        if not os.environ.get("AZURE_OPENAI_ENDPOINT"):
            errors.append("AZURE_OPENAI_ENDPOINT required when ATTACKER_BACKEND=azure")

    return errors


# ---------------------------------------------------------------------------
# Module-level singleton (lazy)
# ---------------------------------------------------------------------------

_config: ServerConfig | None = None


def get_config() -> ServerConfig:
    """Return the module-level ServerConfig singleton.

    Config is constructed once from the current environment. To reload
    (e.g. in tests), call reset_config() first.
    """
    global _config
    if _config is None:
        _config = ServerConfig()
    return _config


def reset_config() -> None:
    """Reset the config singleton (for use in tests only)."""
    global _config
    _config = None
