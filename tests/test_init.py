"""Tests for pyrit_mcp.tools.__init__ — register_all_tools."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest


@pytest.mark.unit
def test_register_all_tools_adds_expected_tools() -> None:
    """register_all_tools should call mcp.add_tool for every exported tool."""
    from pyrit_mcp.tools import __all__ as tool_names
    from pyrit_mcp.tools import register_all_tools

    mcp = MagicMock()
    register_all_tools(mcp)

    assert mcp.add_tool.call_count == len(tool_names)


@pytest.mark.unit
def test_register_all_tools_uses_annotations() -> None:
    """Each registered tool should receive a ToolAnnotations instance."""
    from pyrit_mcp.tools import register_all_tools

    mcp = MagicMock()
    register_all_tools(mcp)

    for call in mcp.add_tool.call_args_list:
        assert "annotations" in call.kwargs
