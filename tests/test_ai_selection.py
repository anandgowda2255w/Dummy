import json
from unittest.mock import patch

from llm.function_selector import select_function


@patch("llm.function_selector.ask_llm")
def test_oee_selection(mock_llm):

    mock_llm.return_value = json.dumps({
        "function": "calculate_oee",
        "arguments": {
            "machine_id": "M001",
            "start_date": None,
            "end_date": None
        }
    })

    result = select_function("Calculate OEE for M001")

    assert result["intent"] == "manufacturing"
    assert result["function"] == "calculate_oee"
    mock_llm.assert_not_called()


@patch("llm.function_selector.ask_llm")
def test_downtime_selection(mock_llm):

    mock_llm.return_value = json.dumps({
        "function": "get_machine_downtime",
        "arguments": {
            "machine_id": "M004",
            "start_date": None,
            "end_date": None
        }
    })

    result = select_function("Show downtime for M004")

    assert result["function"] == "get_machine_downtime"
    mock_llm.assert_not_called()


@patch("llm.function_selector.ask_llm")
def test_compare_selection(mock_llm):

    mock_llm.return_value = json.dumps({
        "function": "compare_machine_analytics",
        "arguments": {
            "machine1": "M001",
            "machine2": "M002",
            "start_date": None,
            "end_date": None
        }
    })

    result = select_function("Compare M001 and M002")

    assert result["function"] == "compare_machine_analytics"
    mock_llm.assert_not_called()


def test_oee_machine_name_beats_machine_keywords():
    result = select_function("OEE of Hydraulic Press")

    assert result["function"] == "calculate_oee"
    assert result["arguments"]["machine_id"] == "M009"
    assert result["arguments"]["start_date"] is None
    assert result["arguments"]["end_date"] is None


def test_oee_analysis_hydraulic_press_machine_selection():
    result = select_function("OEE analysis of Hydraulic Press Machine")

    assert result["function"] == "calculate_oee"
    assert result["arguments"]["machine_id"] == "M009"


def test_oee_analysis_has_no_default_parameters():
    result = select_function("OEE analysis")

    assert result["function"] == "calculate_oee"
    assert result["arguments"]["machine_id"] is None
    assert result["arguments"]["start_date"] is None
    assert result["arguments"]["end_date"] is None


def test_invalid_machine_id_candidate_is_extracted():
    result = select_function("OEE of MM0987")

    assert result["function"] == "calculate_oee"
    assert result["arguments"]["machine_id"] == "MM0987"


def test_invalid_machine_name_candidate_is_extracted():
    result = select_function("OEE of CNCCCD")

    assert result["function"] == "calculate_oee"
    assert result["arguments"]["machine_id"] == "CNCCCD"


def test_conversation():

    result = select_function("Hello")

    assert result["intent"] == "conversational"


def test_gibberish():

    result = select_function("asdfgh")

    assert result["intent"] == "gibberish"
