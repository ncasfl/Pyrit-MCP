"""
Tests for pyrit_mcp dataset and prompt library tools (Domain 3).

Tests cover all 7 dataset tools:
  - pyrit_list_builtin_datasets
  - pyrit_load_dataset
  - pyrit_preview_dataset
  - pyrit_create_custom_dataset
  - pyrit_import_dataset_from_file
  - pyrit_list_session_datasets
  - pyrit_merge_datasets
"""

from __future__ import annotations

import json
import os
import tempfile

import pytest

from pyrit_mcp.utils.db import fetchall, fetchone

# ---------------------------------------------------------------------------
# pyrit_list_builtin_datasets
# ---------------------------------------------------------------------------


@pytest.mark.unit
async def test_list_builtin_datasets_returns_all() -> None:
    from pyrit_mcp.tools.datasets import pyrit_list_builtin_datasets

    result = await pyrit_list_builtin_datasets()
    assert result["status"] == "success"
    data = result["data"]
    assert data["count"] == 12  # all built-in datasets
    assert len(data["datasets"]) == 12
    assert "available_categories" in data


@pytest.mark.unit
async def test_list_builtin_datasets_filter_by_category() -> None:
    from pyrit_mcp.tools.datasets import pyrit_list_builtin_datasets

    result = await pyrit_list_builtin_datasets(filter_category="jailbreak")
    assert result["status"] == "success"
    data = result["data"]
    # jailbreak-classic and jailbreak-roleplay
    assert data["count"] == 2
    for ds in data["datasets"]:
        assert ds["category"] == "jailbreak"


@pytest.mark.unit
async def test_list_builtin_datasets_filter_no_match() -> None:
    from pyrit_mcp.tools.datasets import pyrit_list_builtin_datasets

    result = await pyrit_list_builtin_datasets(filter_category="nonexistent")
    assert result["status"] == "success"
    assert result["data"]["count"] == 0
    assert result["data"]["datasets"] == []


@pytest.mark.unit
async def test_list_builtin_datasets_has_expected_fields() -> None:
    from pyrit_mcp.tools.datasets import pyrit_list_builtin_datasets

    result = await pyrit_list_builtin_datasets()
    ds = result["data"]["datasets"][0]
    assert "name" in ds
    assert "category" in ds
    assert "description" in ds
    assert "approximate_count" in ds


# ---------------------------------------------------------------------------
# pyrit_load_dataset
# ---------------------------------------------------------------------------


@pytest.mark.unit
async def test_load_dataset_success() -> None:
    from pyrit_mcp.tools.datasets import pyrit_load_dataset

    result = await pyrit_load_dataset(dataset_name="cybercrime")
    assert result["status"] == "success"
    data = result["data"]
    assert data["dataset_name"] == "cybercrime"
    assert data["category"] == "cybercrime"
    assert data["prompt_count"] > 0
    assert "dataset_id" in data


@pytest.mark.unit
async def test_load_dataset_persists_to_db() -> None:
    from pyrit_mcp.tools.datasets import pyrit_load_dataset

    await pyrit_load_dataset(dataset_name="cybercrime")
    row = fetchone("SELECT name, category, prompt_count FROM datasets WHERE name = ?", ["cybercrime"])
    assert row is not None
    assert row[0] == "cybercrime"
    assert row[1] == "cybercrime"
    assert row[2] > 0


@pytest.mark.unit
async def test_load_dataset_unknown_name() -> None:
    from pyrit_mcp.tools.datasets import pyrit_load_dataset

    result = await pyrit_load_dataset(dataset_name="totally-fake")
    assert result["status"] == "error"
    assert "totally-fake" in result["error"]
    assert "suggestion" in result


@pytest.mark.unit
async def test_load_dataset_idempotent() -> None:
    from pyrit_mcp.tools.datasets import pyrit_load_dataset

    r1 = await pyrit_load_dataset(dataset_name="cybercrime")
    r2 = await pyrit_load_dataset(dataset_name="cybercrime")
    assert r1["status"] == "success"
    assert r2["status"] == "success"
    # Should be same dataset_id on second load (update, not duplicate)
    assert r2["data"]["dataset_id"] == r1["data"]["dataset_id"]
    # Only one row in DB
    rows = fetchall("SELECT * FROM datasets WHERE name = ?", ["cybercrime"])
    assert len(rows) == 1


@pytest.mark.unit
async def test_load_dataset_with_max_samples() -> None:
    from pyrit_mcp.tools.datasets import pyrit_load_dataset

    result = await pyrit_load_dataset(dataset_name="cybercrime", max_samples=1)
    assert result["status"] == "success"
    assert result["data"]["prompt_count"] <= 1
    assert result["data"]["max_samples_applied"] is True


@pytest.mark.unit
async def test_load_dataset_with_shuffle() -> None:
    from pyrit_mcp.tools.datasets import pyrit_load_dataset

    result = await pyrit_load_dataset(dataset_name="cybercrime", shuffle=True)
    assert result["status"] == "success"
    assert result["data"]["shuffled"] is True


# ---------------------------------------------------------------------------
# pyrit_preview_dataset
# ---------------------------------------------------------------------------


@pytest.mark.unit
async def test_preview_dataset_from_static_samples() -> None:
    from pyrit_mcp.tools.datasets import pyrit_preview_dataset

    result = await pyrit_preview_dataset(dataset_name="jailbreak-classic", n_samples=2)
    assert result["status"] == "success"
    data = result["data"]
    assert data["dataset_name"] == "jailbreak-classic"
    assert len(data["sample_prompts"]) <= 2
    assert data["source"] == "pyrit_builtin"


@pytest.mark.unit
async def test_preview_dataset_from_session_cache() -> None:
    from pyrit_mcp.tools.datasets import pyrit_load_dataset, pyrit_preview_dataset

    # Load first so it's cached in the session DB
    await pyrit_load_dataset(dataset_name="cybercrime")
    result = await pyrit_preview_dataset(dataset_name="cybercrime", n_samples=3)
    assert result["status"] == "success"
    assert result["data"]["source"] == "session_cache"


@pytest.mark.unit
async def test_preview_dataset_unknown_name() -> None:
    from pyrit_mcp.tools.datasets import pyrit_preview_dataset

    result = await pyrit_preview_dataset(dataset_name="nonexistent")
    assert result["status"] == "error"
    assert "nonexistent" in result["error"]


@pytest.mark.unit
async def test_preview_dataset_clamps_n_samples() -> None:
    from pyrit_mcp.tools.datasets import pyrit_preview_dataset

    # n_samples clamped to [1, 20] internally
    result = await pyrit_preview_dataset(dataset_name="jailbreak-classic", n_samples=0)
    assert result["status"] == "success"
    assert result["data"]["samples_shown"] >= 1

    result2 = await pyrit_preview_dataset(dataset_name="jailbreak-classic", n_samples=100)
    assert result2["status"] == "success"
    assert result2["data"]["samples_shown"] <= 20


@pytest.mark.unit
async def test_preview_dataset_no_static_samples_falls_back() -> None:
    from pyrit_mcp.tools.datasets import pyrit_preview_dataset

    # "violence" has no static samples in _SAMPLE_PROMPTS, so it falls back to _load_pyrit_dataset
    result = await pyrit_preview_dataset(dataset_name="violence", n_samples=2)
    assert result["status"] == "success"
    data = result["data"]
    assert data["source"] == "pyrit_builtin"
    assert len(data["sample_prompts"]) > 0


# ---------------------------------------------------------------------------
# pyrit_create_custom_dataset
# ---------------------------------------------------------------------------


@pytest.mark.unit
async def test_create_custom_dataset_success() -> None:
    from pyrit_mcp.tools.datasets import pyrit_create_custom_dataset

    prompts_json = json.dumps(["prompt one", "prompt two", "prompt three"])
    result = await pyrit_create_custom_dataset(
        prompts=prompts_json,
        category="custom",
        dataset_name="my-test-ds",
    )
    assert result["status"] == "success"
    data = result["data"]
    assert data["dataset_name"] == "my-test-ds"
    assert data["prompt_count"] == 3
    assert data["action"] == "created"
    assert data["category"] == "custom"


@pytest.mark.unit
async def test_create_custom_dataset_persists_to_db() -> None:
    from pyrit_mcp.tools.datasets import pyrit_create_custom_dataset

    prompts_json = json.dumps(["hello", "world"])
    await pyrit_create_custom_dataset(
        prompts=prompts_json,
        category="test-cat",
        dataset_name="db-check-ds",
    )
    row = fetchone("SELECT name, category, prompt_count, prompts_json FROM datasets WHERE name = ?", ["db-check-ds"])
    assert row is not None
    assert row[0] == "db-check-ds"
    assert row[1] == "test-cat"
    assert row[2] == 2
    stored = json.loads(row[3])
    assert stored == ["hello", "world"]


@pytest.mark.unit
async def test_create_custom_dataset_overwrite_existing() -> None:
    from pyrit_mcp.tools.datasets import pyrit_create_custom_dataset

    p1 = json.dumps(["a", "b"])
    r1 = await pyrit_create_custom_dataset(prompts=p1, category="v1", dataset_name="overwrite-ds")
    assert r1["data"]["action"] == "created"

    p2 = json.dumps(["x", "y", "z"])
    r2 = await pyrit_create_custom_dataset(prompts=p2, category="v2", dataset_name="overwrite-ds")
    assert r2["data"]["action"] == "updated"
    assert r2["data"]["prompt_count"] == 3
    # Same dataset_id preserved
    assert r2["data"]["dataset_id"] == r1["data"]["dataset_id"]


@pytest.mark.unit
async def test_create_custom_dataset_invalid_json() -> None:
    from pyrit_mcp.tools.datasets import pyrit_create_custom_dataset

    result = await pyrit_create_custom_dataset(
        prompts="not valid json",
        category="custom",
        dataset_name="bad-ds",
    )
    assert result["status"] == "error"
    assert "JSON" in result["error"]


@pytest.mark.unit
async def test_create_custom_dataset_empty_array() -> None:
    from pyrit_mcp.tools.datasets import pyrit_create_custom_dataset

    result = await pyrit_create_custom_dataset(
        prompts="[]",
        category="custom",
        dataset_name="empty-ds",
    )
    assert result["status"] == "error"
    assert "non-empty" in result["error"]


@pytest.mark.unit
async def test_create_custom_dataset_not_array() -> None:
    from pyrit_mcp.tools.datasets import pyrit_create_custom_dataset

    result = await pyrit_create_custom_dataset(
        prompts='"just a string"',
        category="custom",
        dataset_name="str-ds",
    )
    assert result["status"] == "error"


@pytest.mark.unit
async def test_create_custom_dataset_empty_name() -> None:
    from pyrit_mcp.tools.datasets import pyrit_create_custom_dataset

    result = await pyrit_create_custom_dataset(
        prompts='["p1"]',
        category="custom",
        dataset_name="   ",
    )
    assert result["status"] == "error"
    assert "empty" in result["error"]


# ---------------------------------------------------------------------------
# pyrit_import_dataset_from_file
# ---------------------------------------------------------------------------


@pytest.mark.unit
async def test_import_csv_success() -> None:
    from pyrit_mcp.tools.datasets import pyrit_import_dataset_from_file

    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8") as f:
        f.write("prompt,category\n")
        f.write("Hello world,test\n")
        f.write("Second prompt,test\n")
        path = f.name
    try:
        result = await pyrit_import_dataset_from_file(file_path=path, dataset_name="csv-ds")
        assert result["status"] == "success"
        assert result["data"]["prompt_count"] == 2
        assert result["data"]["dataset_name"] == "csv-ds"
    finally:
        os.unlink(path)


@pytest.mark.unit
async def test_import_csv_default_name_from_filename() -> None:
    from pyrit_mcp.tools.datasets import pyrit_import_dataset_from_file

    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8", prefix="myprompts_") as f:
        f.write("prompt\n")
        f.write("A prompt\n")
        path = f.name
    try:
        result = await pyrit_import_dataset_from_file(file_path=path)
        assert result["status"] == "success"
        # Name defaults to file stem
        from pathlib import Path as P

        assert result["data"]["dataset_name"] == P(path).stem
    finally:
        os.unlink(path)


@pytest.mark.unit
async def test_import_csv_with_max_rows() -> None:
    from pyrit_mcp.tools.datasets import pyrit_import_dataset_from_file

    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8") as f:
        f.write("prompt\n")
        for i in range(10):
            f.write(f"Prompt {i}\n")
        path = f.name
    try:
        result = await pyrit_import_dataset_from_file(file_path=path, dataset_name="max-rows-ds", max_rows=3)
        assert result["status"] == "success"
        assert result["data"]["prompt_count"] == 3
    finally:
        os.unlink(path)


@pytest.mark.unit
async def test_import_json_array_of_strings() -> None:
    from pyrit_mcp.tools.datasets import pyrit_import_dataset_from_file

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(["prompt A", "prompt B"], f)
        path = f.name
    try:
        result = await pyrit_import_dataset_from_file(file_path=path, dataset_name="json-str-ds")
        assert result["status"] == "success"
        assert result["data"]["prompt_count"] == 2
    finally:
        os.unlink(path)


@pytest.mark.unit
async def test_import_json_array_of_objects() -> None:
    from pyrit_mcp.tools.datasets import pyrit_import_dataset_from_file

    data = [{"prompt": "obj prompt 1"}, {"prompt": "obj prompt 2"}]
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(data, f)
        path = f.name
    try:
        result = await pyrit_import_dataset_from_file(
            file_path=path, dataset_name="json-obj-ds", prompt_column="prompt"
        )
        assert result["status"] == "success"
        assert result["data"]["prompt_count"] == 2
    finally:
        os.unlink(path)


@pytest.mark.unit
async def test_import_json_with_max_rows() -> None:
    from pyrit_mcp.tools.datasets import pyrit_import_dataset_from_file

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(["a", "b", "c", "d", "e"], f)
        path = f.name
    try:
        result = await pyrit_import_dataset_from_file(file_path=path, dataset_name="json-max-ds", max_rows=2)
        assert result["status"] == "success"
        assert result["data"]["prompt_count"] == 2
    finally:
        os.unlink(path)


@pytest.mark.unit
async def test_import_file_not_found() -> None:
    from pyrit_mcp.tools.datasets import pyrit_import_dataset_from_file

    result = await pyrit_import_dataset_from_file(file_path="/nonexistent/path.csv")
    assert result["status"] == "error"
    assert "not found" in result["error"].lower() or "File not found" in result["error"]


@pytest.mark.unit
async def test_import_unsupported_extension() -> None:
    from pyrit_mcp.tools.datasets import pyrit_import_dataset_from_file

    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write("hello")
        path = f.name
    try:
        result = await pyrit_import_dataset_from_file(file_path=path)
        assert result["status"] == "error"
        assert "Unsupported" in result["error"]
    finally:
        os.unlink(path)


@pytest.mark.unit
async def test_import_csv_empty_prompts() -> None:
    from pyrit_mcp.tools.datasets import pyrit_import_dataset_from_file

    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8") as f:
        f.write("other_col\n")
        f.write("not a prompt\n")
        path = f.name
    try:
        # The prompt column doesn't exist, _read_csv_prompts raises ValueError
        result = await pyrit_import_dataset_from_file(file_path=path, prompt_column="prompt", dataset_name="empty-csv")
        assert result["status"] == "error"
    finally:
        os.unlink(path)


@pytest.mark.unit
async def test_import_overwrites_existing_dataset() -> None:
    from pyrit_mcp.tools.datasets import pyrit_import_dataset_from_file

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(["first"], f)
        path = f.name
    try:
        r1 = await pyrit_import_dataset_from_file(file_path=path, dataset_name="overwrite-import")
        assert r1["status"] == "success"

        # Write new content and re-import
        with open(path, "w", encoding="utf-8") as f2:
            json.dump(["second", "third"], f2)

        r2 = await pyrit_import_dataset_from_file(file_path=path, dataset_name="overwrite-import")
        assert r2["status"] == "success"
        assert r2["data"]["prompt_count"] == 2
        # Same dataset_id
        assert r2["data"]["dataset_id"] == r1["data"]["dataset_id"]
    finally:
        os.unlink(path)


# ---------------------------------------------------------------------------
# pyrit_list_session_datasets
# ---------------------------------------------------------------------------


@pytest.mark.unit
async def test_list_session_datasets_empty() -> None:
    from pyrit_mcp.tools.datasets import pyrit_list_session_datasets

    result = await pyrit_list_session_datasets()
    assert result["status"] == "success"
    assert result["data"]["count"] == 0
    assert result["data"]["datasets"] == []


@pytest.mark.unit
async def test_list_session_datasets_after_load() -> None:
    from pyrit_mcp.tools.datasets import pyrit_list_session_datasets, pyrit_load_dataset

    await pyrit_load_dataset(dataset_name="cybercrime")
    result = await pyrit_list_session_datasets()
    assert result["status"] == "success"
    assert result["data"]["count"] == 1
    ds = result["data"]["datasets"][0]
    assert ds["name"] == "cybercrime"
    assert ds["is_builtin"] is True
    assert ds["prompt_count"] > 0


@pytest.mark.unit
async def test_list_session_datasets_includes_custom() -> None:
    from pyrit_mcp.tools.datasets import (
        pyrit_create_custom_dataset,
        pyrit_list_session_datasets,
    )

    await pyrit_create_custom_dataset(
        prompts='["p1", "p2"]',
        category="custom",
        dataset_name="my-custom",
    )
    result = await pyrit_list_session_datasets()
    assert result["status"] == "success"
    assert result["data"]["count"] == 1
    ds = result["data"]["datasets"][0]
    assert ds["name"] == "my-custom"
    assert ds["is_builtin"] is False


# ---------------------------------------------------------------------------
# pyrit_merge_datasets
# ---------------------------------------------------------------------------


@pytest.mark.unit
async def test_merge_datasets_success() -> None:
    from pyrit_mcp.tools.datasets import (
        pyrit_create_custom_dataset,
        pyrit_merge_datasets,
    )

    await pyrit_create_custom_dataset(prompts='["a", "b"]', category="cat1", dataset_name="ds1")
    await pyrit_create_custom_dataset(prompts='["c", "d"]', category="cat2", dataset_name="ds2")

    result = await pyrit_merge_datasets(
        dataset_names='["ds1", "ds2"]',
        output_name="merged-ds",
    )
    assert result["status"] == "success"
    data = result["data"]
    assert data["prompt_count"] == 4
    assert data["dataset_name"] == "merged-ds"
    assert data["source_datasets"] == ["ds1", "ds2"]


@pytest.mark.unit
async def test_merge_datasets_deduplication() -> None:
    from pyrit_mcp.tools.datasets import (
        pyrit_create_custom_dataset,
        pyrit_merge_datasets,
    )

    await pyrit_create_custom_dataset(prompts='["x", "y"]', category="c", dataset_name="dup1")
    await pyrit_create_custom_dataset(prompts='["y", "z"]', category="c", dataset_name="dup2")

    result = await pyrit_merge_datasets(
        dataset_names='["dup1", "dup2"]',
        output_name="deduped",
        deduplicate=True,
    )
    assert result["status"] == "success"
    assert result["data"]["prompt_count"] == 3  # x, y, z
    assert result["data"]["duplicates_removed"] == 1


@pytest.mark.unit
async def test_merge_datasets_no_deduplication() -> None:
    from pyrit_mcp.tools.datasets import (
        pyrit_create_custom_dataset,
        pyrit_merge_datasets,
    )

    await pyrit_create_custom_dataset(prompts='["x", "y"]', category="c", dataset_name="nodup1")
    await pyrit_create_custom_dataset(prompts='["y", "z"]', category="c", dataset_name="nodup2")

    result = await pyrit_merge_datasets(
        dataset_names='["nodup1", "nodup2"]',
        output_name="not-deduped",
        deduplicate=False,
    )
    assert result["status"] == "success"
    assert result["data"]["prompt_count"] == 4  # x, y, y, z
    assert result["data"]["duplicates_removed"] == 0


@pytest.mark.unit
async def test_merge_datasets_same_category_preserved() -> None:
    from pyrit_mcp.tools.datasets import (
        pyrit_create_custom_dataset,
        pyrit_merge_datasets,
    )

    await pyrit_create_custom_dataset(prompts='["a"]', category="jailbreak", dataset_name="jb1")
    await pyrit_create_custom_dataset(prompts='["b"]', category="jailbreak", dataset_name="jb2")

    result = await pyrit_merge_datasets(
        dataset_names='["jb1", "jb2"]',
        output_name="jb-merged",
    )
    assert result["status"] == "success"
    assert result["data"]["category"] == "jailbreak"


@pytest.mark.unit
async def test_merge_datasets_mixed_category_becomes_merged() -> None:
    from pyrit_mcp.tools.datasets import (
        pyrit_create_custom_dataset,
        pyrit_merge_datasets,
    )

    await pyrit_create_custom_dataset(prompts='["a"]', category="jailbreak", dataset_name="mix1")
    await pyrit_create_custom_dataset(prompts='["b"]', category="cybercrime", dataset_name="mix2")

    result = await pyrit_merge_datasets(
        dataset_names='["mix1", "mix2"]',
        output_name="mixed-merged",
    )
    assert result["status"] == "success"
    assert result["data"]["category"] == "merged"


@pytest.mark.unit
async def test_merge_datasets_invalid_json() -> None:
    from pyrit_mcp.tools.datasets import pyrit_merge_datasets

    result = await pyrit_merge_datasets(
        dataset_names="not json",
        output_name="bad-merge",
    )
    assert result["status"] == "error"
    assert "JSON" in result["error"]


@pytest.mark.unit
async def test_merge_datasets_too_few_names() -> None:
    from pyrit_mcp.tools.datasets import pyrit_merge_datasets

    result = await pyrit_merge_datasets(
        dataset_names='["only-one"]',
        output_name="bad-merge",
    )
    assert result["status"] == "error"
    assert "at least 2" in result["error"]


@pytest.mark.unit
async def test_merge_datasets_empty_list() -> None:
    from pyrit_mcp.tools.datasets import pyrit_merge_datasets

    result = await pyrit_merge_datasets(
        dataset_names="[]",
        output_name="bad-merge",
    )
    assert result["status"] == "error"


@pytest.mark.unit
async def test_merge_datasets_empty_output_name() -> None:
    from pyrit_mcp.tools.datasets import pyrit_merge_datasets

    result = await pyrit_merge_datasets(
        dataset_names='["a", "b"]',
        output_name="  ",
    )
    assert result["status"] == "error"
    assert "empty" in result["error"]


@pytest.mark.unit
async def test_merge_datasets_source_not_found() -> None:
    from pyrit_mcp.tools.datasets import (
        pyrit_create_custom_dataset,
        pyrit_merge_datasets,
    )

    await pyrit_create_custom_dataset(prompts='["a"]', category="c", dataset_name="exists1")

    result = await pyrit_merge_datasets(
        dataset_names='["exists1", "does-not-exist"]',
        output_name="fail-merge",
    )
    assert result["status"] == "error"
    assert "does-not-exist" in result["error"]


@pytest.mark.unit
async def test_merge_datasets_overwrites_existing_output() -> None:
    from pyrit_mcp.tools.datasets import (
        pyrit_create_custom_dataset,
        pyrit_merge_datasets,
    )

    await pyrit_create_custom_dataset(prompts='["a"]', category="c", dataset_name="ow1")
    await pyrit_create_custom_dataset(prompts='["b"]', category="c", dataset_name="ow2")
    await pyrit_create_custom_dataset(prompts='["old"]', category="c", dataset_name="ow-out")

    r1 = await pyrit_merge_datasets(
        dataset_names='["ow1", "ow2"]',
        output_name="ow-out",
    )
    assert r1["status"] == "success"
    assert r1["data"]["prompt_count"] == 2

    # Verify DB has updated prompts
    row = fetchone("SELECT prompts_json FROM datasets WHERE name = ?", ["ow-out"])
    stored = json.loads(row[0])
    assert "a" in stored
    assert "b" in stored
