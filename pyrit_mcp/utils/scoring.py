"""
pyrit_mcp.utils.scoring — Low-level scoring helpers shared across tool modules.

Factored out of tools/scorers.py to prevent circular imports between the
scorers and orchestrators modules (both need substring matching logic).

This module contains only pure, synchronous scoring functions with no DB
or network dependencies so it can be safely imported from anywhere.
"""

from __future__ import annotations

import re


def substring_score(
    text: str,
    keywords: list[str],
    match_mode: str,
) -> tuple[bool, list[str]]:
    """Evaluate text against a keyword list using the specified match mode.

    Args:
        text: Response text to evaluate.
        keywords: List of keyword strings or regex patterns.
        match_mode: ``any`` (any keyword matches), ``all`` (all must match),
            or ``regex`` (first keyword treated as a Python regex pattern).

    Returns:
        Tuple of (matched: bool, matched_keywords: list[str]).
    """
    text_lower = text.lower()
    matched: list[str] = []

    if match_mode == "regex":
        pattern = keywords[0] if keywords else ""
        try:
            if re.search(pattern, text, re.IGNORECASE | re.DOTALL):
                matched.append(pattern)
        except re.error:
            pass
        return bool(matched), matched

    for kw in keywords:
        if kw.lower() in text_lower:
            matched.append(kw)

    if match_mode == "any":
        return bool(matched), matched
    elif match_mode == "all":
        all_matched = len(matched) == len(keywords)
        return all_matched, matched if all_matched else []
    else:
        # Treat unknown mode as "any"
        return bool(matched), matched
