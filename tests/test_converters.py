from __future__ import annotations

import pytest


@pytest.mark.unit
async def test_list_converters() -> None:
    from pyrit_mcp.tools.converters import pyrit_list_converters

    result = await pyrit_list_converters()
    assert result["status"] == "success"
    converters = result["data"]["converters"]
    assert isinstance(converters, list)
    assert len(converters) >= 12


@pytest.mark.unit
async def test_apply_base64() -> None:
    import base64

    from pyrit_mcp.tools.converters import pyrit_apply_converter

    result = await pyrit_apply_converter(converter_name="base64", input_text="hello")
    assert result["status"] == "success"
    assert result["data"]["original"] == "hello"
    converted = result["data"]["converted"]
    # Verify it is valid base64 by decoding
    decoded = base64.b64decode(converted).decode("utf-8")
    assert decoded == "hello"


@pytest.mark.unit
async def test_apply_rot13() -> None:
    from pyrit_mcp.tools.converters import pyrit_apply_converter

    result = await pyrit_apply_converter(converter_name="rot13", input_text="hello")
    assert result["status"] == "success"
    assert result["data"]["original"] == "hello"
    assert result["data"]["converted"] == "uryyb"


@pytest.mark.unit
async def test_apply_leetspeak() -> None:
    from pyrit_mcp.tools.converters import pyrit_apply_converter

    result = await pyrit_apply_converter(converter_name="leetspeak", input_text="hello")
    assert result["status"] == "success"
    assert result["data"]["original"] == "hello"
    converted = result["data"]["converted"]
    # Leetspeak should differ from the original due to character substitutions
    assert converted != "hello"
    assert len(converted) == len("hello")


@pytest.mark.unit
async def test_apply_caesar_cipher() -> None:
    from pyrit_mcp.tools.converters import pyrit_apply_converter

    result = await pyrit_apply_converter(converter_name="caesar_cipher", input_text="abc")
    assert result["status"] == "success"
    assert result["data"]["original"] == "abc"
    converted = result["data"]["converted"]
    # Caesar cipher shifts letters; result should differ from input
    assert converted != "abc"
    assert len(converted) == len("abc")


@pytest.mark.unit
async def test_apply_suffix_injection() -> None:
    from pyrit_mcp.tools.converters import pyrit_apply_converter

    result = await pyrit_apply_converter(converter_name="suffix_injection", input_text="hello")
    assert result["status"] == "success"
    assert result["data"]["original"] == "hello"
    converted = result["data"]["converted"]
    # The converted text should start with the original and have a suffix appended
    assert converted.startswith("hello")
    assert len(converted) > len("hello")


@pytest.mark.unit
async def test_apply_prefix_injection() -> None:
    from pyrit_mcp.tools.converters import pyrit_apply_converter

    result = await pyrit_apply_converter(converter_name="prefix_injection", input_text="hello")
    assert result["status"] == "success"
    assert result["data"]["original"] == "hello"
    converted = result["data"]["converted"]
    # The converted text should end with the original and have a prefix prepended
    assert converted.endswith("hello")
    assert len(converted) > len("hello")


@pytest.mark.unit
async def test_apply_invalid_converter() -> None:
    from pyrit_mcp.tools.converters import pyrit_apply_converter

    result = await pyrit_apply_converter(converter_name="nonexistent_converter", input_text="hello")
    assert result["status"] == "error"


@pytest.mark.unit
async def test_chain_converters() -> None:
    from pyrit_mcp.tools.converters import pyrit_chain_converters

    result = await pyrit_chain_converters(converter_names=["rot13", "base64"], input_text="hello")
    assert result["status"] == "success"
    assert result["data"]["original"] == "hello"
    assert "converted" in result["data"]
    steps = result["data"]["steps"]
    assert isinstance(steps, list)
    assert len(steps) == 2


@pytest.mark.unit
async def test_chain_converters_empty_list() -> None:
    from pyrit_mcp.tools.converters import pyrit_chain_converters

    result = await pyrit_chain_converters(converter_names=[], input_text="hello")
    assert result["status"] == "error"


@pytest.mark.unit
async def test_chain_converters_invalid_name() -> None:
    from pyrit_mcp.tools.converters import pyrit_chain_converters

    result = await pyrit_chain_converters(
        converter_names=["rot13", "totally_fake"], input_text="hello"
    )
    assert result["status"] == "error"


@pytest.mark.unit
async def test_apply_morse_code() -> None:
    from pyrit_mcp.tools.converters import pyrit_apply_converter

    result = await pyrit_apply_converter(converter_name="morse_code", input_text="hello")
    assert result["status"] == "success"
    assert result["data"]["original"] == "hello"
    converted = result["data"]["converted"]
    # Morse code output should contain dots and/or dashes
    assert "." in converted or "-" in converted


@pytest.mark.unit
async def test_apply_character_space_insertion() -> None:
    from pyrit_mcp.tools.converters import pyrit_apply_converter

    result = await pyrit_apply_converter(
        converter_name="character_space_insertion", input_text="hello"
    )
    assert result["status"] == "success"
    assert result["data"]["original"] == "hello"
    converted = result["data"]["converted"]
    # Zero-width spaces (\u200b) should be inserted between characters
    assert "\u200b" in converted
    assert len(converted) > len("hello")


@pytest.mark.unit
async def test_apply_converter_empty_input() -> None:
    from pyrit_mcp.tools.converters import pyrit_apply_converter

    result = await pyrit_apply_converter(converter_name="base64", input_text="")
    assert result["status"] == "success"
    assert result["data"]["original"] == ""
