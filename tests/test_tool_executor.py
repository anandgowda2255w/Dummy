import pytest

from llm.tool_executor import execute_tool


def test_invalid_tool():

    result = execute_tool(
        "dummy_function",
        {}
    )

    assert isinstance(result, dict)
    assert result["status"] == "error"


def test_calculate_oee_missing_params():

    result = execute_tool(
        "calculate_oee",
        {}
    )

    assert isinstance(result, dict)
    assert result["status"] == "error"


def test_compare_missing_arguments():

    result = execute_tool(
        "compare_machine_analytics",
        {}
    )

    assert result["status"] == "error"