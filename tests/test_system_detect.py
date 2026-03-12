"""Tests for pyrit_mcp.utils.system_detect — hardware detection and model recommendation.

Tests cover:
  - Parsing .env.detected files
  - Handling missing .env.detected gracefully
  - Tier matching logic across all 7 tiers
  - Model recommendation output structure
  - Edge cases (exact boundaries, GPU presence)
"""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# get_system_profile tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_get_system_profile_returns_dict_when_no_detected_file() -> None:
    """When .env.detected does not exist, return a dict with empty/default values."""
    from pyrit_mcp.utils.system_detect import get_system_profile

    profile = get_system_profile(env_path=Path("/nonexistent/.env.detected"))

    assert isinstance(profile, dict)
    assert profile["detected"] is False


@pytest.mark.unit
def test_get_system_profile_parses_detected_file(tmp_path: Path) -> None:
    """Parse a well-formed .env.detected file into structured data."""
    from pyrit_mcp.utils.system_detect import get_system_profile

    env_file = tmp_path / ".env.detected"
    env_file.write_text(
        textwrap.dedent("""\
        DETECTED_TOTAL_RAM_GB=768
        DETECTED_AVAILABLE_RAM_GB=752
        DETECTED_CPU_CORES=128
        DETECTED_CPU_MODEL="AMD EPYC 9654 96-Core Processor"
        DETECTED_CPU_SOCKETS=2
        DETECTED_NUMA_NODES=2
        DETECTED_HAS_NVIDIA_GPU=false
        DETECTED_HAS_AMD_GPU=false
        DETECTED_GPU_VRAM_GB=0
        DETECTED_INFERENCE_MODE=cpu
    """)
    )

    profile = get_system_profile(env_path=env_file)
    assert profile["detected"] is True
    assert profile["total_ram_gb"] == 768
    assert profile["available_ram_gb"] == 752
    assert profile["cpu_cores"] == 128
    assert profile["cpu_sockets"] == 2
    assert profile["numa_nodes"] == 2
    assert profile["has_nvidia_gpu"] is False
    assert profile["gpu_vram_gb"] == 0
    assert profile["inference_mode"] == "cpu"


@pytest.mark.unit
def test_get_system_profile_handles_missing_fields(tmp_path: Path) -> None:
    """Partial .env.detected should fill in defaults for missing keys."""
    from pyrit_mcp.utils.system_detect import get_system_profile

    env_file = tmp_path / ".env.detected"
    env_file.write_text("DETECTED_TOTAL_RAM_GB=32\n")

    profile = get_system_profile(env_path=env_file)
    assert profile["detected"] is True
    assert profile["total_ram_gb"] == 32
    assert profile["cpu_cores"] == 0  # default for missing


# ---------------------------------------------------------------------------
# recommend_models tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_recommend_models_tier_1() -> None:
    """8GB RAM should map to Tier 1."""
    from pyrit_mcp.utils.system_detect import recommend_models

    result = recommend_models(available_ram_gb=8)
    assert result["tier_id"] == 1
    assert result["attacker"]["backend"] == "ollama"
    assert "dolphin" in result["attacker"]["model_id"].lower()


@pytest.mark.unit
def test_recommend_models_tier_2() -> None:
    """24GB RAM should map to Tier 2."""
    from pyrit_mcp.utils.system_detect import recommend_models

    result = recommend_models(available_ram_gb=24)
    assert result["tier_id"] == 2


@pytest.mark.unit
def test_recommend_models_tier_3() -> None:
    """48GB RAM should map to Tier 3."""
    from pyrit_mcp.utils.system_detect import recommend_models

    result = recommend_models(available_ram_gb=48)
    assert result["tier_id"] == 3
    assert result["attacker"]["backend"] == "ollama"
    assert result["scorer"]["backend"] == "ollama"


@pytest.mark.unit
def test_recommend_models_tier_5() -> None:
    """200GB RAM should map to Tier 5 with llamacpp attacker."""
    from pyrit_mcp.utils.system_detect import recommend_models

    result = recommend_models(available_ram_gb=200)
    assert result["tier_id"] == 5
    assert result["attacker"]["backend"] == "llamacpp"


@pytest.mark.unit
def test_recommend_models_tier_7() -> None:
    """768GB RAM should map to Tier 7."""
    from pyrit_mcp.utils.system_detect import recommend_models

    result = recommend_models(available_ram_gb=768)
    assert result["tier_id"] == 7
    assert result["attacker"]["quant_id"] == "Q8_0"


@pytest.mark.unit
def test_recommend_models_below_minimum() -> None:
    """RAM below Tier 1 minimum should still return Tier 1 (best effort)."""
    from pyrit_mcp.utils.system_detect import recommend_models

    result = recommend_models(available_ram_gb=4)
    assert result["tier_id"] == 1


@pytest.mark.unit
def test_recommend_models_exact_boundary() -> None:
    """Exact tier boundary (32GB = Tier 3 min) should land in that tier."""
    from pyrit_mcp.utils.system_detect import recommend_models

    result = recommend_models(available_ram_gb=32)
    assert result["tier_id"] == 3


@pytest.mark.unit
def test_recommend_models_includes_compose_profile() -> None:
    """Recommendation should include the Docker compose profile to use."""
    from pyrit_mcp.utils.system_detect import recommend_models

    result = recommend_models(available_ram_gb=300)
    assert "compose_profile" in result
    assert result["compose_profile"] == "full-llamacpp"


@pytest.mark.unit
def test_recommend_models_includes_ram_breakdown() -> None:
    """Recommendation should include RAM allocation breakdown."""
    from pyrit_mcp.utils.system_detect import recommend_models

    result = recommend_models(available_ram_gb=768)
    assert "total_ram_required_gb" in result
    assert "remaining_ram_gb" in result
    assert result["remaining_ram_gb"] >= 0


@pytest.mark.unit
def test_recommend_models_with_gpu() -> None:
    """GPU presence should be noted in the recommendation."""
    from pyrit_mcp.utils.system_detect import recommend_models

    result = recommend_models(available_ram_gb=32, has_gpu=True, gpu_vram_gb=24)
    assert result.get("has_gpu") is True
    assert result.get("gpu_vram_gb") == 24


@pytest.mark.unit
def test_recommend_models_role_filter() -> None:
    """Filtering by role should still return valid recommendations."""
    from pyrit_mcp.utils.system_detect import recommend_models

    result = recommend_models(available_ram_gb=48, role="attacker")
    assert "attacker" in result


# ---------------------------------------------------------------------------
# load_model_catalog / load_tier_profiles tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_load_tier_profiles_returns_list() -> None:
    """tier_profiles.json should parse into a list of tier dicts."""
    from pyrit_mcp.utils.system_detect import load_tier_profiles

    tiers = load_tier_profiles()
    assert isinstance(tiers, list)
    assert len(tiers) == 7
    assert tiers[0]["tier_id"] == 1
    assert tiers[6]["tier_id"] == 7


@pytest.mark.unit
def test_load_model_catalog_returns_list() -> None:
    """model_catalog.json should parse into a list of model dicts."""
    from pyrit_mcp.utils.system_detect import load_model_catalog

    models = load_model_catalog()
    assert isinstance(models, list)
    assert len(models) > 0
    assert all("id" in m for m in models)
