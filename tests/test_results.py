"""
Tests for pyrit_mcp result storage and reporting tools (Domain 5).

Tests cover all 8 results tools:
  - pyrit_list_attacks
  - pyrit_get_attack_results
  - pyrit_get_successful_jailbreaks
  - pyrit_get_failed_attacks
  - pyrit_export_results_csv
  - pyrit_generate_report
  - pyrit_compare_attacks
  - pyrit_clear_session
"""

from __future__ import annotations

import json
import uuid

import pytest

from pyrit_mcp.tools.results import (
    pyrit_clear_session,
    pyrit_compare_attacks,
    pyrit_export_results_csv,
    pyrit_generate_report,
    pyrit_get_attack_results,
    pyrit_get_failed_attacks,
    pyrit_get_successful_jailbreaks,
    pyrit_list_attacks,
)
from pyrit_mcp.utils.db import execute, fetchone

# ---------------------------------------------------------------------------
# Helpers: insert test data directly into the DB
# ---------------------------------------------------------------------------


def _insert_attack(
    target_id: str | None = None,
    dataset_name: str = "test-dataset",
    status: str = "complete",
    orchestrator_type: str = "prompt_sending",
) -> str:
    attack_id = str(uuid.uuid4())
    execute(
        "INSERT INTO attacks (attack_id, target_id, dataset_name, orchestrator_type, status) "
        "VALUES (?, ?, ?, ?, ?)",
        [attack_id, target_id, dataset_name, orchestrator_type, status],
    )
    return attack_id


def _insert_result(
    attack_id: str,
    prompt: str = "Test prompt",
    response: str = "Test response",
    scores: dict | None = None,
) -> str:
    result_id = str(uuid.uuid4())
    execute(
        "INSERT INTO results (result_id, attack_id, prompt_text, response_text, scores_json) "
        "VALUES (?, ?, ?, ?, ?)",
        [result_id, attack_id, prompt, response, json.dumps(scores) if scores else None],
    )
    return result_id


def _insert_target(target_type: str = "openai") -> str:
    target_id = str(uuid.uuid4())
    config = {"api_base": "http://localhost:11434", "model": "test", "api_key_env": ""}
    execute(
        "INSERT INTO targets (target_id, target_type, config_json) VALUES (?, ?, ?)",
        [target_id, target_type, json.dumps(config)],
    )
    return target_id


# ---------------------------------------------------------------------------
# pyrit_list_attacks
# ---------------------------------------------------------------------------


@pytest.mark.unit
async def test_list_attacks_empty() -> None:
    result = await pyrit_list_attacks()
    assert result["status"] == "success"
    assert result["data"]["attacks"] == []
    assert result["data"]["count"] == 0


@pytest.mark.unit
async def test_list_attacks_returns_all() -> None:
    _insert_attack(dataset_name="dataset-a", status="complete")
    _insert_attack(dataset_name="dataset-b", status="running")
    result = await pyrit_list_attacks()
    assert result["status"] == "success"
    assert result["data"]["count"] == 2


@pytest.mark.unit
async def test_list_attacks_filter_by_status() -> None:
    _insert_attack(status="complete")
    _insert_attack(status="running")
    _insert_attack(status="failed")

    result = await pyrit_list_attacks(status_filter="complete")
    assert result["data"]["count"] == 1
    assert result["data"]["attacks"][0]["status"] == "complete"


@pytest.mark.unit
async def test_list_attacks_filter_by_target() -> None:
    t1 = _insert_target()
    t2 = _insert_target()
    _insert_attack(target_id=t1)
    _insert_attack(target_id=t1)
    _insert_attack(target_id=t2)

    result = await pyrit_list_attacks(target_id=t1)
    assert result["data"]["count"] == 2


# ---------------------------------------------------------------------------
# pyrit_get_attack_results
# ---------------------------------------------------------------------------


@pytest.mark.unit
async def test_get_attack_results_not_found() -> None:
    result = await pyrit_get_attack_results(attack_id="nonexistent")
    assert result["status"] == "error"
    assert "suggestion" in result


@pytest.mark.unit
async def test_get_attack_results_returns_results() -> None:
    attack_id = _insert_attack()
    for i in range(5):
        _insert_result(attack_id, prompt=f"Prompt {i}", response=f"Response {i}")

    result = await pyrit_get_attack_results(attack_id=attack_id)
    assert result["status"] == "success"
    data = result["data"]
    assert data["page"]["total"] == 5
    assert len(data["results"]) == 5


@pytest.mark.unit
async def test_get_attack_results_pagination() -> None:
    attack_id = _insert_attack()
    for i in range(10):
        _insert_result(attack_id, prompt=f"Prompt {i}")

    page1 = await pyrit_get_attack_results(attack_id=attack_id, limit=5, offset=0)
    page2 = await pyrit_get_attack_results(attack_id=attack_id, limit=5, offset=5)

    assert len(page1["data"]["results"]) == 5
    assert len(page2["data"]["results"]) == 5
    assert page1["data"]["page"]["has_more"] is True
    assert page2["data"]["page"]["has_more"] is False

    # No duplicate results across pages
    ids_p1 = {r["result_id"] for r in page1["data"]["results"]}
    ids_p2 = {r["result_id"] for r in page2["data"]["results"]}
    assert ids_p1.isdisjoint(ids_p2)


@pytest.mark.unit
async def test_get_attack_results_score_filter() -> None:
    attack_id = _insert_attack()
    scorer_id = "scorer-abc"
    # High-score jailbreak result
    _insert_result(
        attack_id,
        prompt="Jailbreak prompt",
        response="Sure, here is how",
        scores={scorer_id: {"score": 1.0, "matched": True}},
    )
    # Low-score refused result
    _insert_result(
        attack_id,
        prompt="Safe prompt",
        response="I cannot help with that",
        scores={scorer_id: {"score": 0.0, "matched": False}},
    )

    result = await pyrit_get_attack_results(attack_id=attack_id, filter_score_min=0.5)
    assert result["data"]["page"]["count"] == 1
    assert "Jailbreak" in result["data"]["results"][0]["prompt_text"]


# ---------------------------------------------------------------------------
# pyrit_get_successful_jailbreaks
# ---------------------------------------------------------------------------


@pytest.mark.unit
async def test_get_successful_jailbreaks_empty_when_no_scores() -> None:
    attack_id = _insert_attack()
    _insert_result(attack_id, response="response with no scores")

    result = await pyrit_get_successful_jailbreaks(attack_id=attack_id)
    assert result["status"] == "success"
    assert result["data"]["jailbreak_count"] == 0


@pytest.mark.unit
async def test_get_successful_jailbreaks_finds_matches() -> None:
    attack_id = _insert_attack()
    scorer_id = "scorer-xyz"
    _insert_result(
        attack_id,
        scores={scorer_id: {"score": 1.0}},
        response="Sure here is how to...",
    )
    _insert_result(
        attack_id,
        scores={scorer_id: {"score": 0.0}},
        response="I cannot help with that.",
    )

    result = await pyrit_get_successful_jailbreaks(attack_id=attack_id)
    assert result["status"] == "success"
    assert result["data"]["jailbreak_count"] == 1
    assert result["data"]["total_results"] == 2
    assert result["data"]["success_rate"] == 50.0


@pytest.mark.unit
async def test_get_successful_jailbreaks_not_found() -> None:
    result = await pyrit_get_successful_jailbreaks(attack_id="nonexistent")
    assert result["status"] == "error"


# ---------------------------------------------------------------------------
# pyrit_get_failed_attacks
# ---------------------------------------------------------------------------


@pytest.mark.unit
async def test_get_failed_attacks_all_refused() -> None:
    attack_id = _insert_attack()
    _insert_result(attack_id, response="I cannot help with that.")
    _insert_result(attack_id, response="This request violates my guidelines.")

    result = await pyrit_get_failed_attacks(attack_id=attack_id)
    assert result["status"] == "success"
    assert result["data"]["refused_count"] == 2
    assert result["data"]["refusal_rate"] == 100.0


@pytest.mark.unit
async def test_get_failed_attacks_mixed_results() -> None:
    attack_id = _insert_attack()
    scorer_id = "s1"
    _insert_result(attack_id, scores={scorer_id: {"score": 1.0}})  # jailbreak
    _insert_result(attack_id, scores={scorer_id: {"score": 0.0}})  # refused
    _insert_result(attack_id)  # no scores = treated as refused

    result = await pyrit_get_failed_attacks(attack_id=attack_id)
    assert result["data"]["refused_count"] == 2


# ---------------------------------------------------------------------------
# pyrit_generate_report
# ---------------------------------------------------------------------------


@pytest.mark.unit
async def test_generate_report_structure() -> None:
    target_id = _insert_target()
    attack_id = _insert_attack(target_id=target_id, status="complete")
    scorer_id = "report-scorer"
    _insert_result(attack_id, scores={scorer_id: {"score": 1.0}})
    _insert_result(attack_id, scores={scorer_id: {"score": 0.0}})

    result = await pyrit_generate_report(attack_id=attack_id)
    assert result["status"] == "success"

    data = result["data"]
    assert data["report_type"] == "red_team_vulnerability_assessment"
    assert data["attack_id"] == attack_id
    assert "statistics" in data
    assert "top_findings" in data
    assert "note_for_narrator" in data

    stats = data["statistics"]
    assert stats["total_prompts_sent"] == 2
    assert stats["jailbreak_count"] == 1
    assert stats["jailbreak_rate_percent"] == 50.0


@pytest.mark.unit
async def test_generate_report_not_found() -> None:
    result = await pyrit_generate_report(attack_id="nonexistent")
    assert result["status"] == "error"


# ---------------------------------------------------------------------------
# pyrit_compare_attacks
# ---------------------------------------------------------------------------


@pytest.mark.unit
async def test_compare_attacks_improvement() -> None:
    scorer_id = "compare-scorer"
    attack_a = _insert_attack(status="complete")
    attack_b = _insert_attack(status="complete")

    # Attack A: 3 jailbreaks out of 4
    for _ in range(3):
        _insert_result(attack_a, scores={scorer_id: {"score": 1.0}})
    _insert_result(attack_a, scores={scorer_id: {"score": 0.0}})

    # Attack B: 1 jailbreak out of 4 (improvement)
    _insert_result(attack_b, scores={scorer_id: {"score": 1.0}})
    for _ in range(3):
        _insert_result(attack_b, scores={scorer_id: {"score": 0.0}})

    result = await pyrit_compare_attacks(attack_id_a=attack_a, attack_id_b=attack_b)
    assert result["status"] == "success"
    data = result["data"]
    assert data["delta"]["jailbreak_count_change"] == -2
    assert "FEWER" in data["delta"]["interpretation"]


@pytest.mark.unit
async def test_compare_attacks_one_not_found() -> None:
    attack_a = _insert_attack()
    result = await pyrit_compare_attacks(attack_id_a=attack_a, attack_id_b="nonexistent")
    assert result["status"] == "error"


# ---------------------------------------------------------------------------
# pyrit_export_results_csv
# ---------------------------------------------------------------------------


@pytest.mark.unit
async def test_export_results_csv_no_results() -> None:
    attack_id = _insert_attack()
    result = await pyrit_export_results_csv(attack_id=attack_id)
    assert result["status"] == "error"


@pytest.mark.unit
async def test_export_results_csv_success(tmp_path: pytest.TempPathFactory) -> None:
    attack_id = _insert_attack()
    _insert_result(attack_id, prompt="P1", response="R1")
    _insert_result(attack_id, prompt="P2", response="R2")

    out_file = str(tmp_path / "test_export.csv")
    result = await pyrit_export_results_csv(attack_id=attack_id, output_path=out_file)
    assert result["status"] == "success"
    assert result["data"]["row_count"] == 2

    import csv

    with open(out_file) as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 2
    assert rows[0]["prompt_text"] == "P1"


# ---------------------------------------------------------------------------
# pyrit_clear_session
# ---------------------------------------------------------------------------


@pytest.mark.unit
async def test_clear_session_requires_confirm() -> None:
    attack_id = _insert_attack()
    _insert_result(attack_id)

    result = await pyrit_clear_session(confirm=False)
    assert result["status"] == "pending_confirmation"
    # Data should still exist
    row = fetchone("SELECT COUNT(*) FROM results")
    assert row[0] == 1


@pytest.mark.unit
async def test_clear_session_deletes_all_data() -> None:
    target_id = _insert_target()
    attack_id = _insert_attack(target_id=target_id)
    _insert_result(attack_id)
    _insert_result(attack_id)

    result = await pyrit_clear_session(confirm=True)
    assert result["status"] == "success"
    assert result["data"]["cleared"] is True

    # All tables should be empty
    for table in ("targets", "attacks", "results"):
        row = fetchone(f"SELECT COUNT(*) FROM {table}")
        assert row[0] == 0, f"Table {table} should be empty after clear"
