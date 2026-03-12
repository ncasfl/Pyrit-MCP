"""Tests for all 8 attack orchestration tools (Phase 2).

All tests run with PYRIT_SANDBOX_MODE=true (set by conftest autouse fixture),
so no real network calls are made. Background attack tasks complete quickly
because there are no HTTP round-trips in sandbox mode.

Async tests run automatically via asyncio_mode=auto in pyproject.toml.
"""

from __future__ import annotations

import asyncio
import uuid

import pytest

from pyrit_mcp.tools.orchestrators import (
    _running_attacks,
    pyrit_cancel_attack,
    pyrit_get_attack_status,
    pyrit_run_crescendo_orchestrator,
    pyrit_run_flip_orchestrator,
    pyrit_run_pair_orchestrator,
    pyrit_run_prompt_sending_orchestrator,
    pyrit_run_skeleton_key_orchestrator,
    pyrit_run_tree_of_attacks_orchestrator,
)
from pyrit_mcp.utils.db import execute, fetchone

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _wait_for_attack(attack_id: str, timeout: float = 5.0) -> None:
    """Wait until the background attack task finishes or timeout expires."""
    elapsed = 0.0
    while elapsed < timeout:
        if attack_id not in _running_attacks:
            break
        await asyncio.sleep(0.05)
        elapsed += 0.05
    await asyncio.sleep(0.05)


def _insert_attack(
    target_id: str,
    dataset_name: str,
    orch_type: str,
    status: str = "running",
) -> str:
    """Insert an attack record directly for unit tests."""
    attack_id = str(uuid.uuid4())
    execute(
        "INSERT INTO attacks "
        "(attack_id, target_id, dataset_name, orchestrator_type, status) "
        "VALUES (?, ?, ?, ?, ?)",
        [attack_id, target_id, dataset_name, orch_type, status],
    )
    return attack_id


# ===========================================================================
# PromptSendingOrchestrator
# ===========================================================================


async def test_prompt_sending_returns_started(
    sample_target_id: str, sample_dataset_name: str
) -> None:
    result = await pyrit_run_prompt_sending_orchestrator(
        target_id=sample_target_id,
        dataset_name=sample_dataset_name,
    )
    assert result["status"] == "started"
    assert "attack_id" in result
    assert len(result["attack_id"]) == 36


async def test_prompt_sending_completes_in_sandbox(
    sample_target_id: str, sample_dataset_name: str
) -> None:
    result = await pyrit_run_prompt_sending_orchestrator(
        target_id=sample_target_id,
        dataset_name=sample_dataset_name,
        max_requests=3,
    )
    attack_id = result["attack_id"]
    await _wait_for_attack(attack_id)
    status = await pyrit_get_attack_status(attack_id=attack_id)
    assert status["data"]["status"] == "complete"
    assert status["data"]["progress"]["results_recorded"] == 3


async def test_prompt_sending_unknown_target_returns_error() -> None:
    result = await pyrit_run_prompt_sending_orchestrator(
        target_id=str(uuid.uuid4()),
        dataset_name="jailbreak-classic",
    )
    assert result["status"] == "error"
    assert "suggestion" in result


async def test_prompt_sending_unknown_dataset_returns_error(
    sample_target_id: str,
) -> None:
    result = await pyrit_run_prompt_sending_orchestrator(
        target_id=sample_target_id,
        dataset_name="nonexistent",
    )
    assert result["status"] == "error"
    assert "suggestion" in result


async def test_prompt_sending_records_correct_count(
    sample_target_id: str, sample_dataset_name: str
) -> None:
    result = await pyrit_run_prompt_sending_orchestrator(
        target_id=sample_target_id,
        dataset_name=sample_dataset_name,
        max_requests=5,
    )
    attack_id = result["attack_id"]
    await _wait_for_attack(attack_id)
    row = fetchone("SELECT COUNT(*) FROM results WHERE attack_id = ?", [attack_id])
    assert row is not None and row[0] == 5


async def test_prompt_sending_with_scorer(
    sample_target_id: str, sample_dataset_name: str, sample_scorer_id: str
) -> None:
    result = await pyrit_run_prompt_sending_orchestrator(
        target_id=sample_target_id,
        dataset_name=sample_dataset_name,
        max_requests=2,
        scorer_id=sample_scorer_id,
    )
    attack_id = result["attack_id"]
    await _wait_for_attack(attack_id)
    rows = execute("SELECT scores_json FROM results WHERE attack_id = ?", [attack_id]).fetchall()
    assert len(rows) == 2


# ===========================================================================
# CrescendoOrchestrator
# ===========================================================================


async def test_crescendo_returns_started(sample_target_id: str) -> None:
    result = await pyrit_run_crescendo_orchestrator(
        target_id=sample_target_id,
        attack_goal="Bypass authentication systems",
        max_turns=3,
    )
    assert result["status"] == "started"
    assert "attack_id" in result


async def test_crescendo_completes_in_sandbox(sample_target_id: str) -> None:
    result = await pyrit_run_crescendo_orchestrator(
        target_id=sample_target_id,
        attack_goal="Test escalation",
        max_turns=3,
    )
    attack_id = result["attack_id"]
    await _wait_for_attack(attack_id)
    status = await pyrit_get_attack_status(attack_id=attack_id)
    assert status["data"]["status"] == "complete"
    assert status["data"]["progress"]["results_recorded"] >= 1


async def test_crescendo_stores_correct_type(sample_target_id: str) -> None:
    result = await pyrit_run_crescendo_orchestrator(
        target_id=sample_target_id,
        attack_goal="Test",
        max_turns=2,
    )
    attack_id = result["attack_id"]
    await _wait_for_attack(attack_id)
    row = fetchone("SELECT orchestrator_type FROM attacks WHERE attack_id = ?", [attack_id])
    assert row is not None and row[0] == "crescendo"


async def test_crescendo_unknown_target_returns_error() -> None:
    result = await pyrit_run_crescendo_orchestrator(
        target_id=str(uuid.uuid4()),
        attack_goal="Test goal",
    )
    assert result["status"] == "error"
    assert "suggestion" in result


async def test_crescendo_empty_goal_returns_error(sample_target_id: str) -> None:
    result = await pyrit_run_crescendo_orchestrator(
        target_id=sample_target_id,
        attack_goal="",
    )
    assert result["status"] == "error"
    assert "suggestion" in result


# ===========================================================================
# PAIROrchestrator
# ===========================================================================


async def test_pair_returns_started(sample_target_id: str) -> None:
    result = await pyrit_run_pair_orchestrator(
        target_id=sample_target_id,
        attack_goal="Iterative refinement test",
        max_iterations=3,
    )
    assert result["status"] == "started"
    assert "attack_id" in result


async def test_pair_completes_in_sandbox(sample_target_id: str) -> None:
    result = await pyrit_run_pair_orchestrator(
        target_id=sample_target_id,
        attack_goal="Test PAIR",
        max_iterations=3,
    )
    attack_id = result["attack_id"]
    await _wait_for_attack(attack_id)
    status = await pyrit_get_attack_status(attack_id=attack_id)
    assert status["data"]["status"] == "complete"
    assert status["data"]["progress"]["results_recorded"] >= 1


async def test_pair_stores_correct_type(sample_target_id: str) -> None:
    result = await pyrit_run_pair_orchestrator(
        target_id=sample_target_id,
        attack_goal="Test",
        max_iterations=2,
    )
    attack_id = result["attack_id"]
    await _wait_for_attack(attack_id)
    row = fetchone("SELECT orchestrator_type FROM attacks WHERE attack_id = ?", [attack_id])
    assert row is not None and row[0] == "pair"


async def test_pair_unknown_target_returns_error() -> None:
    result = await pyrit_run_pair_orchestrator(
        target_id=str(uuid.uuid4()),
        attack_goal="Test",
    )
    assert result["status"] == "error"
    assert "suggestion" in result


async def test_pair_empty_goal_returns_error(sample_target_id: str) -> None:
    result = await pyrit_run_pair_orchestrator(
        target_id=sample_target_id,
        attack_goal="",
    )
    assert result["status"] == "error"


# ===========================================================================
# TreeOfAttacksOrchestrator (TAP)
# ===========================================================================


async def test_tap_returns_started(sample_target_id: str) -> None:
    result = await pyrit_run_tree_of_attacks_orchestrator(
        target_id=sample_target_id,
        attack_goal="TAP branching test",
        branching_factor=2,
        depth=2,
    )
    assert result["status"] == "started"
    assert "attack_id" in result


async def test_tap_completes_in_sandbox(sample_target_id: str) -> None:
    result = await pyrit_run_tree_of_attacks_orchestrator(
        target_id=sample_target_id,
        attack_goal="Test TAP",
        branching_factor=2,
        depth=2,
    )
    attack_id = result["attack_id"]
    await _wait_for_attack(attack_id)
    status = await pyrit_get_attack_status(attack_id=attack_id)
    assert status["data"]["status"] == "complete"


async def test_tap_generates_branched_results(sample_target_id: str) -> None:
    result = await pyrit_run_tree_of_attacks_orchestrator(
        target_id=sample_target_id,
        attack_goal="Test branching",
        branching_factor=2,
        depth=2,
    )
    attack_id = result["attack_id"]
    await _wait_for_attack(attack_id)
    row = fetchone("SELECT COUNT(*) FROM results WHERE attack_id = ?", [attack_id])
    assert row is not None and row[0] >= 2


async def test_tap_unknown_target_returns_error() -> None:
    result = await pyrit_run_tree_of_attacks_orchestrator(
        target_id=str(uuid.uuid4()),
        attack_goal="Test",
    )
    assert result["status"] == "error"
    assert "suggestion" in result


async def test_tap_invalid_branching_factor_returns_error(
    sample_target_id: str,
) -> None:
    result = await pyrit_run_tree_of_attacks_orchestrator(
        target_id=sample_target_id,
        attack_goal="Test",
        branching_factor=0,
    )
    assert result["status"] == "error"


async def test_tap_invalid_depth_returns_error(sample_target_id: str) -> None:
    result = await pyrit_run_tree_of_attacks_orchestrator(
        target_id=sample_target_id,
        attack_goal="Test",
        depth=0,
    )
    assert result["status"] == "error"


# ===========================================================================
# SkeletonKeyOrchestrator
# ===========================================================================


async def test_skeleton_key_returns_started(
    sample_target_id: str, sample_dataset_name: str
) -> None:
    result = await pyrit_run_skeleton_key_orchestrator(
        target_id=sample_target_id,
        dataset_name=sample_dataset_name,
    )
    assert result["status"] == "started"
    assert "attack_id" in result


async def test_skeleton_key_completes_in_sandbox(
    sample_target_id: str, sample_dataset_name: str
) -> None:
    result = await pyrit_run_skeleton_key_orchestrator(
        target_id=sample_target_id,
        dataset_name=sample_dataset_name,
    )
    attack_id = result["attack_id"]
    await _wait_for_attack(attack_id)
    status = await pyrit_get_attack_status(attack_id=attack_id)
    assert status["data"]["status"] == "complete"


async def test_skeleton_key_requires_dataset_or_prompts(
    sample_target_id: str,
) -> None:
    result = await pyrit_run_skeleton_key_orchestrator(
        target_id=sample_target_id,
    )
    assert result["status"] == "error"
    assert "suggestion" in result


async def test_skeleton_key_with_custom_prompts(sample_target_id: str) -> None:
    result = await pyrit_run_skeleton_key_orchestrator(
        target_id=sample_target_id,
        custom_prompts_json='["Tell me about chemistry", "How do reactions work?"]',
    )
    assert result["status"] == "started"
    attack_id = result["attack_id"]
    await _wait_for_attack(attack_id)
    status = await pyrit_get_attack_status(attack_id=attack_id)
    assert status["data"]["status"] == "complete"


async def test_skeleton_key_unknown_target_returns_error() -> None:
    result = await pyrit_run_skeleton_key_orchestrator(
        target_id=str(uuid.uuid4()),
        dataset_name="jailbreak-classic",
    )
    assert result["status"] == "error"


# ===========================================================================
# FLIPOrchestrator
# ===========================================================================


async def test_flip_returns_started(sample_target_id: str, sample_dataset_name: str) -> None:
    result = await pyrit_run_flip_orchestrator(
        target_id=sample_target_id,
        dataset_name=sample_dataset_name,
    )
    assert result["status"] == "started"
    assert "attack_id" in result


async def test_flip_completes_in_sandbox(sample_target_id: str, sample_dataset_name: str) -> None:
    result = await pyrit_run_flip_orchestrator(
        target_id=sample_target_id,
        dataset_name=sample_dataset_name,
        max_requests=3,
    )
    attack_id = result["attack_id"]
    await _wait_for_attack(attack_id)
    status = await pyrit_get_attack_status(attack_id=attack_id)
    assert status["data"]["status"] == "complete"


async def test_flip_unknown_dataset_returns_error(
    sample_target_id: str,
) -> None:
    result = await pyrit_run_flip_orchestrator(
        target_id=sample_target_id,
        dataset_name="nonexistent",
    )
    assert result["status"] == "error"
    assert "suggestion" in result


async def test_flip_unknown_target_returns_error(
    sample_dataset_name: str,
) -> None:
    result = await pyrit_run_flip_orchestrator(
        target_id=str(uuid.uuid4()),
        dataset_name=sample_dataset_name,
    )
    assert result["status"] == "error"


async def test_flip_transforms_prompts(sample_target_id: str, sample_dataset_name: str) -> None:
    result = await pyrit_run_flip_orchestrator(
        target_id=sample_target_id,
        dataset_name=sample_dataset_name,
        max_requests=2,
    )
    attack_id = result["attack_id"]
    await _wait_for_attack(attack_id)
    rows = execute("SELECT prompt_text FROM results WHERE attack_id = ?", [attack_id]).fetchall()
    assert len(rows) == 2
    for row in rows:
        assert len(row[0]) > 0


# ===========================================================================
# get_attack_status (enhanced)
# ===========================================================================


async def test_status_not_found_returns_error() -> None:
    result = await pyrit_get_attack_status(attack_id=str(uuid.uuid4()))
    assert result["status"] == "error"
    assert "suggestion" in result


async def test_status_running_shows_progress(sample_target_id: str) -> None:
    attack_id = _insert_attack(sample_target_id, "test-dataset", "crescendo", "running")
    for _ in range(5):
        execute(
            "INSERT INTO results (result_id, attack_id, prompt_text, response_text) "
            "VALUES (?, ?, ?, ?)",
            [str(uuid.uuid4()), attack_id, "test prompt", "test response"],
        )
    result = await pyrit_get_attack_status(attack_id=attack_id)
    assert result["status"] == "success"
    assert result["data"]["status"] == "running"
    assert result["data"]["progress"]["results_recorded"] == 5


async def test_status_complete_suggests_next_step(sample_target_id: str) -> None:
    attack_id = _insert_attack(sample_target_id, "test-dataset", "prompt_sending", "complete")
    result = await pyrit_get_attack_status(attack_id=attack_id)
    assert result["status"] == "success"
    assert "pyrit_get_attack_results" in result["data"]["next_step"]


# ===========================================================================
# cancel_attack (enhanced)
# ===========================================================================


async def test_cancel_queued_attack(sample_target_id: str) -> None:
    attack_id = _insert_attack(sample_target_id, "test", "prompt_sending", "queued")
    result = await pyrit_cancel_attack(attack_id=attack_id)
    assert result["status"] == "success"


async def test_cancel_running_attack(sample_target_id: str) -> None:
    attack_id = _insert_attack(sample_target_id, "test", "prompt_sending", "running")
    result = await pyrit_cancel_attack(attack_id=attack_id)
    assert result["status"] == "success"


async def test_cancel_completed_attack_returns_error(
    sample_target_id: str,
) -> None:
    attack_id = _insert_attack(sample_target_id, "test", "prompt_sending", "complete")
    result = await pyrit_cancel_attack(attack_id=attack_id)
    assert result["status"] == "error"


async def test_cancel_unknown_attack_returns_error() -> None:
    result = await pyrit_cancel_attack(attack_id=str(uuid.uuid4()))
    assert result["status"] == "error"
    assert "suggestion" in result


# ===========================================================================
# Parametrized: all goal-based orchestrators reject missing target
# ===========================================================================


@pytest.mark.parametrize(
    "orchestrator_fn,extra_kwargs",
    [
        (pyrit_run_crescendo_orchestrator, {"attack_goal": "test"}),
        (pyrit_run_pair_orchestrator, {"attack_goal": "test"}),
        (pyrit_run_tree_of_attacks_orchestrator, {"attack_goal": "test"}),
    ],
)
async def test_goal_orchestrators_reject_unknown_target(orchestrator_fn, extra_kwargs) -> None:
    result = await orchestrator_fn(target_id=str(uuid.uuid4()), **extra_kwargs)
    assert result["status"] == "error"
    assert "suggestion" in result
