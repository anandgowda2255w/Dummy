from llm.assistant import process_query


def test_process_query_returns_dict():

    result = process_query("Hello")

    assert isinstance(result, dict)


def test_process_query_conversation():

    result = process_query("Hi")

    assert result["intent"] == "conversational"


def test_oee_by_machine_name_asks_only_for_dates():
    result = process_query("OEE of Hydraulic Press")

    assert result["intent"] == "manufacturing"
    assert result["needs_params"] is True
    assert result["needs_machine"] is False
    assert result["needs_dates"] is True
    assert result["arguments"]["machine_id"] == "M009"
    assert result["pending_state"]["function"] == "calculate_oee"
    assert result["pending_state"]["arguments"]["machine_id"] == "M009"


def test_oee_by_machine_id_asks_only_for_dates():
    result = process_query("OEE of M001")

    assert result["needs_params"] is True
    assert result["needs_machine"] is False
    assert result["needs_dates"] is True
    assert result["arguments"]["machine_id"] == "M001"


def test_missing_machine_and_dates_has_no_defaults():
    result = process_query("OEE analysis")

    assert result["needs_params"] is True
    assert result["needs_machine"] is True
    assert result["needs_dates"] is True
    assert result["arguments"]["machine_id"] is None
    assert result["arguments"]["start_date"] is None
    assert result["arguments"]["end_date"] is None


def test_invalid_machine_id_stops_before_dates():
    result = process_query("OEE of M011")

    assert result["error"] is True
    assert result["needs_params"] is False
    assert result["pending_state"] is None
    assert "Machine M011 does not exist in the database." in result["reply"]


def test_invalid_machine_id_like_candidate_stops_before_dates():
    result = process_query("OEE of MM0987")

    assert result["error"] is True
    assert result["needs_params"] is False
    assert result["pending_state"] is None
    assert "Machine MM0987 does not exist in the database." in result["reply"]


def test_invalid_machine_name_stops_before_dates():
    result = process_query("OEE of CNCCCD")

    assert result["error"] is True
    assert result["needs_params"] is False
    assert result["pending_state"] is None
    assert "Machine 'CNCCCD' does not exist in the database." in result["reply"]


def test_no_previous_context_reuse_after_completed_query():
    previous = [{"role": "user", "content": "OEE of Hydraulic Press"}]
    result = process_query("OEE analysis", chat_history=previous, pending_state=None)

    assert result["needs_machine"] is True
    assert result["arguments"]["machine_id"] is None
    assert result["arguments"]["start_date"] is None
    assert result["arguments"]["end_date"] is None
