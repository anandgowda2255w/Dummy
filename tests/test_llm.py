from llm.llm_handler import check_ollama_status


def test_check_ollama_status_returns_bool():
    result = check_ollama_status()
    assert isinstance(result, bool)