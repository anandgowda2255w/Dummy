import pytest
from llm.llm_handler import check_ollama_status, ask_llm


def test_ollama_status():
    assert check_ollama_status() in [True, False]


def test_ask_llm():
    if not check_ollama_status():
        pytest.skip("Ollama is not running.")

    reply = ask_llm("Say hello in one word.")

    assert isinstance(reply, str)
    assert len(reply) > 0