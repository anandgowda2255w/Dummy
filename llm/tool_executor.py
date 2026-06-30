from backend.function_registry import FUNCTION_REGISTRY


def execute_tool(function_name, arguments):
    """Execute a registered function with the given arguments. Returns structured result."""
    if function_name not in FUNCTION_REGISTRY:
        return {
            "status": "error",
            "message": "Invalid machine selected or unknown analysis type. Please try again."
        }
    try:
        # Filter out null/None arguments so functions use defaults
        clean_args = {k: v for k, v in arguments.items() if v is not None}
        function = FUNCTION_REGISTRY[function_name]
        return function(**clean_args)
    except TypeError:
        return {"status": "error", "message": "Analysis failed. Please check the parameters and try again."}
    except Exception:
        return {"status": "error", "message": "Analysis temporarily unavailable. Please try again."}
