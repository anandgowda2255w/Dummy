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


def test_ambiguous_machine_waits_for_selection():
    result = process_query("rejection analysis of cnc")

    assert result["needs_params"] is True
    assert result["needs_machine"] is True
    assert result["pending_state"]["function"] == "get_machine_rejection"
    assert result["pending_state"]["arguments"]["machine_id"] is None
    assert "CNC Lathe 1 (M001)" in result["reply"]
    assert "CNC Lathe 2 (M002)" in result["reply"]


def test_pending_machine_selection_resumes_previous_request():
    first = process_query("rejection analysis of cnc")
    result = process_query("CNC Lathe 1", pending_state=first["pending_state"])

    assert result["needs_params"] is True
    assert result["needs_machine"] is False
    assert result["needs_dates"] is True
    assert result["pending_state"]["function"] == "get_machine_rejection"
    assert result["pending_state"]["arguments"]["machine_id"] == "M001"


def test_plant_keyword_never_becomes_machine():
    result = process_query("plant production summary")

    assert result["needs_machine"] is False
    assert "machine_id" not in result["arguments"]


def test_machine_downtime_from_not_running_phrase():
    result = process_query("Why was Hydraulic Press not running during April?")

    assert result["function_name"] == "get_machine_downtime"
    assert result["arguments"]["machine_id"] == "M009"
    assert result["arguments"]["start_date"] == "2026-04-01"
    assert result["arguments"]["end_date"] == "2026-04-30"


def test_natural_language_explicit_date_range_keeps_end_date():
    result = process_query("OEE of M002 from April 5 2026 to 5 May 2026")

    assert result["function_name"] == "calculate_oee"
    assert result["arguments"]["start_date"] == "2026-04-05"
    assert result["arguments"]["end_date"] == "2026-05-05"
