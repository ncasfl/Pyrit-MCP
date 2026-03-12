"""Tests for all scorer tools (Phase 2).

Covers: substring scorer (Phase 1), LLM scorer, classifier scorer,
batch scoring, cost guard, and score distribution.
"""

from __future__ import annotations

import json
import uuid

import pytest

from pyrit_mcp.tools.scorers import (
    pyrit_configure_classifier_scorer,
    pyrit_configure_llm_scorer,
    pyrit_configure_substring_scorer,
    pyrit_get_score_distribution,
    pyrit_list_scorers,
    pyrit_score_attack_results,
    pyrit_score_response,
)
from pyrit_mcp.utils.db import execute


def _insert_attack_with_results(n_results: int) -> str:
    """Insert a completed attack with n response rows for scoring tests."""
    target_id = str(uuid.uuid4())
    execute(
        "INSERT INTO targets (target_id, target_type, config_json) VALUES (?, ?, ?)",
        [target_id, "openai", json.dumps({"api_base": "http://test", "model": "m"})],
    )
    attack_id = str(uuid.uuid4())
    execute(
        "INSERT INTO attacks "
        "(attack_id, target_id, dataset_name, orchestrator_type, status) "
        "VALUES (?, ?, ?, ?, ?)",
        [attack_id, target_id, "test", "prompt_sending", "complete"],
    )
    responses = [
        "Sure, here is how to do it step by step:",
        "I cannot and will not help with that.",
        "Step 1: Begin by gathering materials.",
        "I am unable to assist with harmful activities.",
        "Of course! Let me walk you through this.",
    ]
    for i in range(n_results):
        execute(
            "INSERT INTO results (result_id, attack_id, prompt_text, response_text) "
            "VALUES (?, ?, ?, ?)",
            [str(uuid.uuid4()), attack_id, f"Prompt {i}", responses[i % len(responses)]],
        )
    return attack_id


# ===========================================================================
# pyrit_configure_substring_scorer (regression)
# ===========================================================================


async def test_substring_configures_successfully() -> None:
    r = await pyrit_configure_substring_scorer(
        keywords='["sure, here", "step 1:"]', match_mode="any"
    )
    assert r["status"] == "success"
    assert r["data"]["scorer_type"] == "substring"


async def test_substring_invalid_json_returns_error() -> None:
    r = await pyrit_configure_substring_scorer(keywords="not json")
    assert r["status"] == "error" and "suggestion" in r


async def test_substring_invalid_mode_returns_error() -> None:
    r = await pyrit_configure_substring_scorer(keywords='["kw"]', match_mode="bad")
    assert r["status"] == "error" and "suggestion" in r


async def test_substring_empty_keywords_returns_error() -> None:
    r = await pyrit_configure_substring_scorer(keywords="[]")
    assert r["status"] == "error"


async def test_substring_regex_mode() -> None:
    r = await pyrit_configure_substring_scorer(
        keywords='["(step \\\\d+|here is how)"]', match_mode="regex"
    )
    assert r["status"] == "success" and r["data"]["match_mode"] == "regex"


async def test_substring_all_mode() -> None:
    r = await pyrit_configure_substring_scorer(keywords='["kw1", "kw2"]', match_mode="all")
    assert r["status"] == "success" and r["data"]["match_mode"] == "all"


# ===========================================================================
# pyrit_configure_llm_scorer
# ===========================================================================


async def test_llm_scorer_openai() -> None:
    r = await pyrit_configure_llm_scorer(
        model="gpt-4o",
        api_key_env="SCORER_KEY",
        scoring_task="Score for harm.",
        backend_type="openai",
        base_url="https://api.openai.com/v1",
    )
    assert r["status"] == "success"
    assert r["data"]["scorer_type"] == "llm"


async def test_llm_scorer_ollama() -> None:
    r = await pyrit_configure_llm_scorer(
        model="llama3.1:70b",
        backend_type="ollama",
        base_url="http://localhost:11434",
        scoring_task="Judge if harmful. Score 1-10.",
    )
    assert r["status"] == "success"


async def test_llm_scorer_does_not_store_key_value() -> None:
    import os

    os.environ["ACTUAL_LLM_KEY"] = "sk-secret9999"
    r = await pyrit_configure_llm_scorer(
        model="gpt-4o",
        api_key_env="ACTUAL_LLM_KEY",
        scoring_task="Evaluate.",
        backend_type="openai",
        base_url="https://api.openai.com/v1",
    )
    from pyrit_mcp.utils.db import execute as _ex

    row = _ex(
        "SELECT config_json FROM scorers WHERE scorer_id = ?", [r["data"]["scorer_id"]]
    ).fetchone()
    assert "sk-secret9999" not in row[0]


async def test_llm_scorer_empty_model_returns_error() -> None:
    r = await pyrit_configure_llm_scorer(
        model="",
        scoring_task="Eval.",
        backend_type="openai",
        base_url="https://api.openai.com/v1",
    )
    assert r["status"] == "error" and "suggestion" in r


async def test_llm_scorer_empty_base_url_returns_error() -> None:
    r = await pyrit_configure_llm_scorer(
        model="gpt-4o",
        scoring_task="Eval.",
        backend_type="openai",
        base_url="",
    )
    assert r["status"] == "error" and "suggestion" in r


async def test_llm_scorer_empty_task_returns_error() -> None:
    r = await pyrit_configure_llm_scorer(
        model="gpt-4o",
        scoring_task="",
        backend_type="openai",
        base_url="https://api.openai.com/v1",
    )
    assert r["status"] == "error" and "suggestion" in r


# ===========================================================================
# pyrit_configure_classifier_scorer
# ===========================================================================


async def test_classifier_scorer_configures() -> None:
    r = await pyrit_configure_classifier_scorer(
        model_name_or_path="unitary/toxic-bert",
        categories='["toxic", "threat"]',
    )
    assert r["status"] == "success" and r["data"]["scorer_type"] == "classifier"


async def test_classifier_scorer_local_path() -> None:
    r = await pyrit_configure_classifier_scorer(
        model_name_or_path="/models/toxic-bert",
        categories='["harmful"]',
    )
    assert r["status"] == "success"


async def test_classifier_scorer_empty_model_returns_error() -> None:
    r = await pyrit_configure_classifier_scorer(model_name_or_path="", categories='["toxic"]')
    assert r["status"] == "error" and "suggestion" in r


async def test_classifier_scorer_bad_categories_json_returns_error() -> None:
    r = await pyrit_configure_classifier_scorer(
        model_name_or_path="unitary/toxic-bert",
        categories="not json",
    )
    assert r["status"] == "error" and "suggestion" in r


async def test_classifier_scorer_empty_categories_returns_error() -> None:
    r = await pyrit_configure_classifier_scorer(
        model_name_or_path="unitary/toxic-bert",
        categories="[]",
    )
    assert r["status"] == "error"


# ===========================================================================
# pyrit_score_response
# ===========================================================================


async def test_score_response_substring_match() -> None:
    s = await pyrit_configure_substring_scorer(
        keywords='["sure, here", "step 1:"]', match_mode="any"
    )
    r = await pyrit_score_response(
        response_text="Sure, here is how step 1: works.", scorer_id=s["data"]["scorer_id"]
    )
    assert r["status"] == "success" and r["data"]["score"] == 1.0 and r["data"]["matched"] is True


async def test_score_response_substring_no_match() -> None:
    s = await pyrit_configure_substring_scorer(keywords='["sure, here"]', match_mode="any")
    r = await pyrit_score_response(
        response_text="I cannot help with that.", scorer_id=s["data"]["scorer_id"]
    )
    assert r["status"] == "success" and r["data"]["score"] == 0.0 and r["data"]["matched"] is False


async def test_score_response_unknown_scorer_returns_error() -> None:
    r = await pyrit_score_response(response_text="Some text", scorer_id=str(uuid.uuid4()))
    assert r["status"] == "error" and "suggestion" in r


async def test_score_response_all_mode_partial_keywords() -> None:
    s = await pyrit_configure_substring_scorer(keywords='["kw1", "kw2"]', match_mode="all")
    sid = s["data"]["scorer_id"]
    r1 = await pyrit_score_response(response_text="contains kw1 but not the other", scorer_id=sid)
    assert r1["data"]["matched"] is False
    r2 = await pyrit_score_response(response_text="contains kw1 and kw2 both here", scorer_id=sid)
    assert r2["data"]["matched"] is True


async def test_score_response_regex_mode() -> None:
    s = await pyrit_configure_substring_scorer(keywords='["step \\\\d+"]', match_mode="regex")
    r = await pyrit_score_response(
        response_text="Step 1: do this. Step 2: do that.", scorer_id=s["data"]["scorer_id"]
    )
    assert r["data"]["matched"] is True


# ===========================================================================
# pyrit_score_attack_results (batch + cost guard)
# ===========================================================================


async def test_batch_score_substring_no_confirmation_needed(sample_scorer_id: str) -> None:
    attack_id = _insert_attack_with_results(3)
    r = await pyrit_score_attack_results(attack_id=attack_id, scorer_id=sample_scorer_id)
    assert r["status"] == "success" and r["data"]["scored_count"] == 3


async def test_batch_score_llm_requires_confirmation() -> None:
    llm = await pyrit_configure_llm_scorer(
        model="gpt-4o",
        api_key_env="K",
        scoring_task="Evaluate.",
        backend_type="openai",
        base_url="https://api.openai.com/v1",
    )
    attack_id = _insert_attack_with_results(5)
    r = await pyrit_score_attack_results(
        attack_id=attack_id,
        scorer_id=llm["data"]["scorer_id"],
        confirm_cost=False,
    )
    assert r["status"] == "pending_confirmation"
    assert "estimate" in r


async def test_batch_score_llm_proceeds_with_confirmation() -> None:
    llm = await pyrit_configure_llm_scorer(
        model="gpt-4o",
        api_key_env="K",
        scoring_task="Evaluate.",
        backend_type="openai",
        base_url="https://api.openai.com/v1",
    )
    attack_id = _insert_attack_with_results(3)
    r = await pyrit_score_attack_results(
        attack_id=attack_id,
        scorer_id=llm["data"]["scorer_id"],
        confirm_cost=True,
    )
    assert r["status"] == "success" and r["data"]["scored_count"] == 3


async def test_batch_score_unknown_attack_returns_error(sample_scorer_id: str) -> None:
    r = await pyrit_score_attack_results(attack_id=str(uuid.uuid4()), scorer_id=sample_scorer_id)
    assert r["status"] == "error" and "suggestion" in r


async def test_batch_score_unknown_scorer_returns_error() -> None:
    attack_id = _insert_attack_with_results(2)
    r = await pyrit_score_attack_results(attack_id=attack_id, scorer_id=str(uuid.uuid4()))
    assert r["status"] == "error" and "suggestion" in r


async def test_batch_score_updates_db(sample_scorer_id: str) -> None:
    attack_id = _insert_attack_with_results(3)
    await pyrit_score_attack_results(attack_id=attack_id, scorer_id=sample_scorer_id)
    rows = execute("SELECT scores_json FROM results WHERE attack_id = ?", [attack_id]).fetchall()
    scored = [r for r in rows if r[0] is not None]
    assert len(scored) == 3


# ===========================================================================
# pyrit_get_score_distribution
# ===========================================================================


async def test_score_distribution_returns_correct_stats(sample_scorer_id: str) -> None:
    attack_id = _insert_attack_with_results(5)
    rows = execute("SELECT result_id FROM results WHERE attack_id = ?", [attack_id]).fetchall()
    scores = [1.0, 0.0, 1.0, 0.0, 1.0]
    for i, (rid,) in enumerate(rows):
        execute(
            "UPDATE results SET scores_json = ? WHERE result_id = ?",
            [json.dumps({sample_scorer_id: {"score": scores[i]}}), rid],
        )
    r = await pyrit_get_score_distribution(attack_id=attack_id, scorer_id=sample_scorer_id)
    assert r["status"] == "success"
    assert r["data"]["total_scored"] == 5
    assert r["data"]["match_count"] == 3
    assert r["data"]["jailbreak_rate"] == pytest.approx(0.6)


async def test_score_distribution_no_scores(sample_scorer_id: str) -> None:
    attack_id = _insert_attack_with_results(3)
    r = await pyrit_get_score_distribution(attack_id=attack_id, scorer_id=sample_scorer_id)
    assert r["status"] == "success" and r["data"]["total_scored"] == 0


async def test_score_distribution_unknown_attack_returns_error(sample_scorer_id: str) -> None:
    r = await pyrit_get_score_distribution(attack_id=str(uuid.uuid4()), scorer_id=sample_scorer_id)
    assert r["status"] == "error" and "suggestion" in r


# ===========================================================================
# pyrit_list_scorers
# ===========================================================================


async def test_list_scorers_empty() -> None:
    r = await pyrit_list_scorers()
    assert r["status"] == "success" and r["data"]["count"] == 0


async def test_list_scorers_all_types() -> None:
    await pyrit_configure_substring_scorer(keywords='["kw"]', match_mode="any")
    await pyrit_configure_llm_scorer(
        model="gpt-4o",
        scoring_task="Eval.",
        backend_type="openai",
        base_url="https://api.openai.com/v1",
    )
    await pyrit_configure_classifier_scorer(
        model_name_or_path="unitary/toxic-bert",
        categories='["toxic"]',
    )
    r = await pyrit_list_scorers()
    assert r["data"]["count"] == 3
    types = {s["scorer_type"] for s in r["data"]["scorers"]}
    assert types == {"substring", "llm", "classifier"}


async def test_list_scorers_no_api_key_values() -> None:
    import os

    os.environ["SECRET_TEST_KEY"] = "sk-supersecret99999"
    await pyrit_configure_llm_scorer(
        model="gpt-4o",
        api_key_env="SECRET_TEST_KEY",
        scoring_task="Eval.",
        backend_type="openai",
        base_url="https://api.openai.com/v1",
    )
    r = await pyrit_list_scorers()
    assert "sk-supersecret99999" not in json.dumps(r)
