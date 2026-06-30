import ollama
import requests

MODEL_NAME = "qwen2.5:3b"


def check_ollama_status():
    """Returns True if Ollama is running and the model is available."""
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=3)
        if response.status_code == 200:
            models = response.json().get("models", [])
            model_names = [m.get("name", "") for m in models]
            return any(MODEL_NAME in name for name in model_names)
        return False
    except Exception:
        return False


def ask_llm(prompt):
    response = ollama.chat(
        model=MODEL_NAME,
        messages=[{"role": "user", "content": prompt}]
    )
    return response["message"]["content"]


def ask_llm_with_history(messages):
    """Send a full conversation history to the LLM."""
    response = ollama.chat(
        model=MODEL_NAME,
        messages=messages
    )
    return response["message"]["content"]
