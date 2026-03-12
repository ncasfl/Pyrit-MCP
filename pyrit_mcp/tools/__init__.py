"""
pyrit_mcp.tools — All MCP tool functions (Phase 1 + Phase 2).

This module exports all tool functions for registration by server.py.
server.py calls register_all_tools(mcp) to attach each function to the
FastMCP instance with its description and MCP annotations.

Phase 1 tools:
  Domain 1 — Targets (6 tools)
  Domain 2 — Orchestrators (3 tools)
  Domain 3 — Datasets (3 tools)
  Domain 4 — Scorers (3 tools)
  Domain 5 — Results (8 tools)

Phase 2 tools (added):
  Domain 2 — Orchestrators (5 more: crescendo, pair, tap, skeleton_key, flip)
  Domain 3 — Datasets (4 more: create_custom, import_from_file, list_session, merge)
  Domain 4 — Scorers (4 more: llm, classifier, score_attack_results, score_distribution)
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from pyrit_mcp.tools.backends import (
    pyrit_benchmark_backend,
    pyrit_configure_attacker_backend,
    pyrit_configure_scorer_backend,
    pyrit_estimate_attack_cost,
    pyrit_list_backend_options,
    pyrit_list_ollama_models,
    pyrit_pull_ollama_model,
    pyrit_recommend_models,
    pyrit_test_backend_connectivity,
)
from pyrit_mcp.tools.converters import (
    pyrit_apply_converter,
    pyrit_chain_converters,
    pyrit_list_converters,
)
from pyrit_mcp.tools.datasets import (
    pyrit_create_custom_dataset,
    pyrit_import_dataset_from_file,
    pyrit_list_builtin_datasets,
    pyrit_list_session_datasets,
    pyrit_load_dataset,
    pyrit_merge_datasets,
    pyrit_preview_dataset,
)
from pyrit_mcp.tools.orchestrators import (
    pyrit_cancel_attack,
    pyrit_get_attack_status,
    pyrit_run_crescendo_orchestrator,
    pyrit_run_flip_orchestrator,
    pyrit_run_pair_orchestrator,
    pyrit_run_prompt_sending_orchestrator,
    pyrit_run_skeleton_key_orchestrator,
    pyrit_run_tree_of_attacks_orchestrator,
)
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
from pyrit_mcp.tools.scorers import (
    pyrit_configure_classifier_scorer,
    pyrit_configure_llm_scorer,
    pyrit_configure_substring_scorer,
    pyrit_get_score_distribution,
    pyrit_list_scorers,
    pyrit_score_attack_results,
    pyrit_score_response,
)
from pyrit_mcp.tools.targets import (
    pyrit_configure_azure_target,
    pyrit_configure_http_target,
    pyrit_configure_openai_target,
    pyrit_list_targets,
    pyrit_remove_target,
    pyrit_test_target_connectivity,
)

__all__ = [
    # Domain 7: Backends (Phase 3)
    "pyrit_apply_converter",
    "pyrit_benchmark_backend",
    "pyrit_cancel_attack",
    "pyrit_chain_converters",
    "pyrit_clear_session",
    "pyrit_compare_attacks",
    "pyrit_configure_attacker_backend",
    "pyrit_configure_azure_target",
    "pyrit_configure_classifier_scorer",
    # Domain 1: Targets
    "pyrit_configure_http_target",
    # Domain 4: Scorers (Phase 2)
    "pyrit_configure_llm_scorer",
    "pyrit_configure_openai_target",
    "pyrit_configure_scorer_backend",
    # Domain 4: Scorers (Phase 1)
    "pyrit_configure_substring_scorer",
    # Domain 3: Datasets (Phase 2)
    "pyrit_create_custom_dataset",
    "pyrit_estimate_attack_cost",
    "pyrit_export_results_csv",
    "pyrit_generate_report",
    "pyrit_get_attack_results",
    "pyrit_get_attack_status",
    "pyrit_get_failed_attacks",
    "pyrit_get_score_distribution",
    "pyrit_get_successful_jailbreaks",
    "pyrit_import_dataset_from_file",
    # Domain 5: Results
    "pyrit_list_attacks",
    "pyrit_list_backend_options",
    # Domain 3: Datasets (Phase 1)
    "pyrit_list_builtin_datasets",
    "pyrit_list_converters",
    "pyrit_list_ollama_models",
    "pyrit_list_scorers",
    "pyrit_list_session_datasets",
    "pyrit_list_targets",
    "pyrit_load_dataset",
    "pyrit_merge_datasets",
    "pyrit_preview_dataset",
    "pyrit_pull_ollama_model",
    "pyrit_recommend_models",
    "pyrit_remove_target",
    # Domain 2: Orchestrators (Phase 2)
    "pyrit_run_crescendo_orchestrator",
    "pyrit_run_flip_orchestrator",
    "pyrit_run_pair_orchestrator",
    # Domain 2: Orchestrators (Phase 1)
    "pyrit_run_prompt_sending_orchestrator",
    "pyrit_run_skeleton_key_orchestrator",
    "pyrit_run_tree_of_attacks_orchestrator",
    "pyrit_score_attack_results",
    "pyrit_score_response",
    "pyrit_test_backend_connectivity",
    "pyrit_test_target_connectivity",
]


def register_all_tools(mcp: FastMCP) -> None:
    """Register all Phase 1 + Phase 2 + Phase 3 tools onto the FastMCP instance."""
    from mcp.types import ToolAnnotations

    def _ann(
        read_only: bool = False,
        destructive: bool = False,
        idempotent: bool = False,
    ) -> ToolAnnotations:
        return ToolAnnotations(
            readOnlyHint=read_only,
            destructiveHint=destructive,
            idempotentHint=idempotent,
        )

    # ── Domain 1: Targets ─────────────────────────────────────────────────
    mcp.add_tool(
        pyrit_configure_http_target,
        description="Register an HTTP endpoint as the target application under test. Returns target_id.",
        annotations=_ann(destructive=False),
    )
    mcp.add_tool(
        pyrit_configure_openai_target,
        description="Register an OpenAI-compatible API (OpenAI, Ollama, LM Studio, vLLM, Groq) as the target. Returns target_id.",
        annotations=_ann(destructive=False),
    )
    mcp.add_tool(
        pyrit_configure_azure_target,
        description="Register an Azure OpenAI deployment as the target. Reads credentials from env vars. Returns target_id.",
        annotations=_ann(destructive=False),
    )
    mcp.add_tool(
        pyrit_list_targets,
        description="List all target applications registered in this session.",
        annotations=_ann(read_only=True),
    )
    mcp.add_tool(
        pyrit_remove_target,
        description="Permanently remove a registered target. Requires confirm=true.",
        annotations=_ann(destructive=True),
    )
    mcp.add_tool(
        pyrit_test_target_connectivity,
        description="Send a lightweight probe to verify a target is reachable. Run before launching attacks.",
        annotations=_ann(read_only=True),
    )

    # ── Domain 2: Orchestrators ────────────────────────────────────────────
    mcp.add_tool(
        pyrit_run_prompt_sending_orchestrator,
        description="Fire a dataset of adversarial prompts at a target. Returns attack_id immediately. Poll with pyrit_get_attack_status.",
        annotations=_ann(destructive=True),
    )
    mcp.add_tool(
        pyrit_run_crescendo_orchestrator,
        description="Multi-turn escalating Crescendo attack. Starts innocuously and escalates. Returns attack_id immediately.",
        annotations=_ann(destructive=True),
    )
    mcp.add_tool(
        pyrit_run_pair_orchestrator,
        description="PAIR iterative refinement attack. Adapts prompts based on target rejections. Returns attack_id immediately.",
        annotations=_ann(destructive=True),
    )
    mcp.add_tool(
        pyrit_run_tree_of_attacks_orchestrator,
        description="TAP tree-of-attacks with pruning. Explores branching attack variants. Returns attack_id immediately.",
        annotations=_ann(destructive=True),
    )
    mcp.add_tool(
        pyrit_run_skeleton_key_orchestrator,
        description="Skeleton Key: inject a priming message to disable safety, then send follow-up prompts. Returns attack_id immediately.",
        annotations=_ann(destructive=True),
    )
    mcp.add_tool(
        pyrit_run_flip_orchestrator,
        description="FLIP attack: encode prompts with character reversal to bypass surface-form filters. Returns attack_id immediately.",
        annotations=_ann(destructive=True),
    )
    mcp.add_tool(
        pyrit_get_attack_status,
        description="Poll status and progress of a running attack campaign. Returns status, percent complete, result count.",
        annotations=_ann(read_only=True),
    )
    mcp.add_tool(
        pyrit_cancel_attack,
        description="Cancel a running or queued attack campaign. Results collected so far are preserved.",
        annotations=_ann(destructive=True),
    )

    # ── Domain 3: Datasets ─────────────────────────────────────────────────
    mcp.add_tool(
        pyrit_list_builtin_datasets,
        description="List all PyRIT built-in adversarial prompt datasets with descriptions and approximate counts.",
        annotations=_ann(read_only=True),
    )
    mcp.add_tool(
        pyrit_load_dataset,
        description="Load a named built-in dataset into the session for use in attack campaigns. Idempotent.",
        annotations=_ann(idempotent=True),
    )
    mcp.add_tool(
        pyrit_preview_dataset,
        description="Show sample prompts from a dataset without loading it. Use to verify content before attacking.",
        annotations=_ann(read_only=True),
    )
    mcp.add_tool(
        pyrit_create_custom_dataset,
        description="Create a custom dataset from a JSON array of prompts provided inline. Overwrites if name exists.",
        annotations=_ann(destructive=False),
    )
    mcp.add_tool(
        pyrit_import_dataset_from_file,
        description="Import prompts from a local CSV or JSON file in the /datasets volume mount.",
        annotations=_ann(destructive=False),
    )
    mcp.add_tool(
        pyrit_list_session_datasets,
        description="List all datasets currently loaded in this session (built-in and custom).",
        annotations=_ann(read_only=True),
    )
    mcp.add_tool(
        pyrit_merge_datasets,
        description="Merge multiple loaded datasets into a single new dataset with optional deduplication.",
        annotations=_ann(destructive=False),
    )

    # ── Domain 4: Scorers ──────────────────────────────────────────────────
    mcp.add_tool(
        pyrit_configure_substring_scorer,
        description="Configure a deterministic keyword/substring scorer. Free, no LLM required.",
        annotations=_ann(destructive=False),
    )
    mcp.add_tool(
        pyrit_configure_llm_scorer,
        description="Configure an LLM-as-judge scorer. Supports OpenAI, Ollama, Azure. Incurs API costs.",
        annotations=_ann(destructive=False),
    )
    mcp.add_tool(
        pyrit_configure_classifier_scorer,
        description="Configure a HuggingFace harm classifier scorer. Free, deterministic, uses pyrit-scorer sidecar.",
        annotations=_ann(destructive=False),
    )
    mcp.add_tool(
        pyrit_score_response,
        description="Score a single response text using a configured scorer. Use to test scorers before campaigns.",
        annotations=_ann(read_only=True),
    )
    mcp.add_tool(
        pyrit_score_attack_results,
        description="Batch-score all results from a completed attack. LLM scorers require confirm_cost=True after cost estimate.",
        annotations=_ann(destructive=False),
    )
    mcp.add_tool(
        pyrit_get_score_distribution,
        description="Get aggregate jailbreak rate, score distribution, and top findings for a scored attack.",
        annotations=_ann(read_only=True),
    )
    mcp.add_tool(
        pyrit_list_scorers,
        description="List all scorers configured in the current session.",
        annotations=_ann(read_only=True),
    )

    # ── Domain 5: Results ──────────────────────────────────────────────────
    mcp.add_tool(
        pyrit_list_attacks,
        description="List all attack campaigns in this session with status and metadata.",
        annotations=_ann(read_only=True),
    )
    mcp.add_tool(
        pyrit_get_attack_results,
        description="Retrieve paginated raw prompt/response pairs from an attack campaign.",
        annotations=_ann(read_only=True),
    )
    mcp.add_tool(
        pyrit_get_successful_jailbreaks,
        description="Return only results where the target was successfully jailbroken.",
        annotations=_ann(read_only=True),
    )
    mcp.add_tool(
        pyrit_get_failed_attacks,
        description="Return prompts where the target successfully refused the attack.",
        annotations=_ann(read_only=True),
    )
    mcp.add_tool(
        pyrit_export_results_csv,
        description="Export all results from an attack campaign to a CSV file.",
        annotations=_ann(destructive=False),
    )
    mcp.add_tool(
        pyrit_generate_report,
        description="Return structured JSON data for Claude to narrate as a vulnerability report.",
        annotations=_ann(read_only=True),
    )
    mcp.add_tool(
        pyrit_compare_attacks,
        description="Compare jailbreak rates and findings between two attack campaigns.",
        annotations=_ann(read_only=True),
    )
    mcp.add_tool(
        pyrit_clear_session,
        description="Permanently delete ALL session data. Irreversible. Requires confirm=true.",
        annotations=_ann(destructive=True),
    )

    # ── Domain 7: Backends (Phase 3) ─────────────────────────────────────
    mcp.add_tool(
        pyrit_configure_attacker_backend,
        description="Switch the attacker LLM backend at runtime. Specify backend type, model, and URL.",
        annotations=_ann(destructive=False),
    )
    mcp.add_tool(
        pyrit_configure_scorer_backend,
        description="Switch the scorer LLM backend at runtime. Specify backend type, model, and URL.",
        annotations=_ann(destructive=False),
    )
    mcp.add_tool(
        pyrit_list_backend_options,
        description="Show current attacker and scorer backend configuration and all available backend types.",
        annotations=_ann(read_only=True),
    )
    mcp.add_tool(
        pyrit_test_backend_connectivity,
        description="Verify a configured backend (attacker or scorer) is reachable. Returns latency.",
        annotations=_ann(read_only=True),
    )
    mcp.add_tool(
        pyrit_estimate_attack_cost,
        description="Estimate token usage and cost for an attack campaign against a loaded dataset.",
        annotations=_ann(read_only=True),
    )
    mcp.add_tool(
        pyrit_recommend_models,
        description="Return ranked model recommendations based on available RAM and hardware.",
        annotations=_ann(read_only=True),
    )
    mcp.add_tool(
        pyrit_pull_ollama_model,
        description="Pull a model into Ollama. Requires confirm_size_gb=true to start the download.",
        annotations=_ann(destructive=False),
    )
    mcp.add_tool(
        pyrit_list_ollama_models,
        description="List all models currently available in the local Ollama instance.",
        annotations=_ann(read_only=True),
    )
    mcp.add_tool(
        pyrit_benchmark_backend,
        description="Run an inference speed test on a configured backend. Returns tokens/sec.",
        annotations=_ann(read_only=True),
    )

    # ── Domain 6: Converters (Phase 4) ────────────────────────────────────
    mcp.add_tool(
        pyrit_list_converters,
        description="List all available prompt converters with descriptions.",
        annotations=_ann(read_only=True),
    )
    mcp.add_tool(
        pyrit_apply_converter,
        description="Apply a single converter to transform a prompt string. Use to test obfuscation before attacks.",
        annotations=_ann(read_only=True),
    )
    mcp.add_tool(
        pyrit_chain_converters,
        description="Apply a sequence of converters in order to a prompt string. Returns intermediate steps.",
        annotations=_ann(read_only=True),
    )
