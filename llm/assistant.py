"""
assistant.py — Core conversation orchestrator.

Responsibilities:
  1. Classify intent (conversational / manufacturing / gibberish / incomplete / out_of_scope)
  2. Extract parameters from query ONLY (no automatic context memory reuse)
  3. Resolve machine names → machine IDs  (NEW: machine resolution layer)
  4. Resolve natural-language dates      (NEW: date resolver)
  5. Validate parameters in priority order (NEW: validation before asking)
  6. Detect missing required parameters
  7. Execute the tool when all parameters are present
  8. Generate natural-language summary via LLM
  9. Generate recommendations
 10. Return structured response dict used by app.py

KEY RULE: Do NOT automatically reuse machine IDs or dates from previous queries.
          Current query always has highest priority.
"""

import re
import time
from llm.function_selector import (
    select_function,
    extract_machine_mentions,
    _has_plant_scope,
    GIBBERISH_REPLY,
    INCOMPLETE_REPLY,
)
from llm.tool_executor import execute_tool
from llm.llm_handler import ask_llm
from llm.machine_resolver import get_resolver
from llm.date_resolver import (
    resolve_dates,
    validate_date_range,
    _extract_explicit_dates,
    detect_invalid_date_strings,
)
from analytics.analytics_engine import get_db_date_range, get_all_machines

# -------------------------------------------------------
# REQUIRED PARAMETERS PER FUNCTION
# -------------------------------------------------------

REQUIRED_PARAMS = {
    "calculate_oee":                          ["machine_id", "start_date", "end_date"],
    "get_downtime_analytics":                 ["start_date", "end_date"],
    "get_machine_downtime":                   ["machine_id", "start_date", "end_date"],
    "get_rejection_analytics":                ["start_date", "end_date"],
    "get_machine_rejection":                  ["machine_id", "start_date", "end_date"],
    "compare_machine_analytics":              ["machine1", "machine2", "start_date", "end_date"],
    "get_production_summary":                 ["start_date", "end_date"],
    "get_plant_production_summary":           ["start_date", "end_date"],
    "get_machine_production_summary":         ["machine_id", "start_date", "end_date"],
    "get_maintenance_recommendation":         ["start_date", "end_date"],
    "get_machine_maintenance_recommendation": ["machine_id", "start_date", "end_date"],
}

# Which parameters need UI controls (machine picker / date range picker)
MACHINE_PARAMS = {"machine_id", "machine1", "machine2"}
DATE_PARAMS = {"start_date", "end_date"}

# -------------------------------------------------------
# RECOMMENDATIONS
# -------------------------------------------------------

RECOMMENDATIONS = {
    "calculate_oee": [
        "🔧 Schedule downtime windows to improve Availability.",
        "⚡ Optimize cycle times to boost Performance.",
        "✅ Tighten quality checks to raise the Quality score.",
        "📊 Target OEE ≥ 85% (World-Class benchmark).",
    ],
    "get_downtime_analytics": [
        "🔩 Schedule preventive maintenance for top downtime machines.",
        "📋 Analyse recurring downtime reasons and address root causes.",
        "⏱️ Implement SMED to reduce setup/changeover losses.",
    ],
    "get_machine_downtime": [
        "🔍 Investigate the top downtime reason for this machine.",
        "📅 Plan dedicated maintenance slots to reduce unplanned stops.",
        "🚨 Review machine alerts linked to frequent downtime events.",
    ],
    "get_rejection_analytics": [
        "🔎 Inspect tooling on highest-rejection machines.",
        "📐 Review process parameters causing defects.",
        "📈 Implement SPC to catch quality drift early.",
    ],
    "get_machine_rejection": [
        "🛠️ Check tooling wear and calibration for this machine.",
        "📋 Analyse daily rejection spikes for common causes.",
        "✅ Add in-process inspection checkpoints.",
    ],
    "compare_machine_analytics": [
        "🔬 Investigate why the weaker machine underperforms.",
        "🔄 Apply best practices from the better machine.",
        "📋 Schedule maintenance on the machine with higher downtime.",
    ],
    "get_production_summary": [
        "📦 Focus on increasing utilization of underperforming machines.",
        "🔗 Balance workload across machines to reduce bottlenecks.",
        "📈 Target overall rejection rate below 3%.",
    ],
    "get_plant_production_summary": [
        "📦 Focus on increasing utilization of underperforming machines.",
        "🔗 Balance workload across machines to reduce bottlenecks.",
        "📈 Target overall rejection rate below 3%.",
    ],
    "get_machine_production_summary": [
        "📅 Review days with production dips for root causes.",
        "⚙️ Check if downtime spikes align with low production days.",
        "🎯 Compare daily output against target to spot shortfalls.",
    ],
    "get_maintenance_recommendation": [
        "🗓️ Create a preventive maintenance schedule based on alert patterns.",
        "🔧 Prioritize machines with both high downtime AND high rejection.",
        "📊 Track MTBF (Mean Time Between Failures) to improve planning.",
    ],
    "get_machine_maintenance_recommendation": [
        "🔧 Schedule immediate inspection based on the alerts above.",
        "📅 Plan a dedicated maintenance window for this machine.",
        "📊 Monitor MTBF trend after maintenance to confirm improvement.",
    ],
}

FOLLOW_UPS: dict = {}  # Follow-up Actions removed per spec §10

SCOPE_SELECTION_TYPES = {
    "get_downtime_analytics": "downtime",
    "get_rejection_analytics": "rejection",
    "get_production_summary": "production",
}

SCOPE_LABELS = {
    "downtime": "Downtime",
    "rejection": "Rejection",
    "production": "Production",
}


# -------------------------------------------------------
# CONSOLE LOGGING — AI FUNCTION SELECTION  (Req #13)
# -------------------------------------------------------

def _log_function_selection(function_name: str | None, arguments: dict | None = None, reason: str | None = None):
    """
    Log the AI-selected function and its parameters to the console.
    Never shown in the chat UI — debugging/testing only.
    """
    separator = "=" * 40
    print(f"\n{separator}")
    print("AI Function Selection")
    print(separator)

    if function_name:
        print(f"Selected Function: {function_name}")
        if arguments:
            print("\nParameters:")
            for key, value in arguments.items():
                if value is not None:
                    print(f"  {key:<15}: {value}")
    else:
        print("No matching function found.")
        if reason:
            print(f"\nReason:\n  {reason}")

    print(separator)


def _log_pipeline(user_query, intent=None, function_name=None, extracted=None,
                  resolved=None, validation=None, missing=None,
                  executed=None, elapsed=None, errors=None):
    separator = "=" * 40
    print(f"\n{separator}")
    print("AI Pipeline")
    print(separator)
    print(f"User Query: {user_query}")
    print(f"Detected Intent: {intent}")
    print(f"Selected Function: {function_name}")
    print(f"Extracted Parameters: {extracted}")
    print(f"Resolved Parameters: {resolved}")
    print(f"Validation Result: {validation}")
    print(f"Missing Parameters: {missing}")
    print(f"Executed Function: {executed}")
    print(f"Execution Time: {elapsed}")
    print(f"Errors: {errors}")
    print(separator)


# -------------------------------------------------------
# DETECT MISSING REQUIRED PARAMS
# -------------------------------------------------------

def get_missing_params(function_name, arguments):
    required = REQUIRED_PARAMS.get(function_name, [])
    return [p for p in required if not arguments.get(p)]


def get_missing_machine_params(function_name, arguments):
    required = REQUIRED_PARAMS.get(function_name, [])
    return [p for p in required if p in MACHINE_PARAMS and not arguments.get(p)]


def get_missing_date_params(function_name, arguments):
    required = REQUIRED_PARAMS.get(function_name, [])
    return [p for p in required if p in DATE_PARAMS and not arguments.get(p)]


def _requires_scope_selection(function_name, user_query, arguments):
    """
    Broad downtime/rejection/production requests need a plant-vs-machine
    choice before backend function selection is considered final.
    """
    if function_name not in SCOPE_SELECTION_TYPES:
        return False
    if _has_plant_scope(user_query):
        return False
    return not any(arguments.get(p) for p in MACHINE_PARAMS)


def _scope_selection_response(function_name, arguments):
    selection_type = SCOPE_SELECTION_TYPES[function_name]
    label = SCOPE_LABELS.get(selection_type, "Analysis")
    pending_state = {
        "selection_required": True,
        "selection_type": selection_type,
        "function": None,
        "arguments": arguments,
    }
    return {
        "intent": "manufacturing",
        "reply": f"Please select the {label} analysis type.",
        "needs_params": True,
        "needs_machine": False,
        "needs_dates": False,
        "missing_machine_params": [],
        "pending_state": pending_state,
        "arguments": arguments,
        "recommendations": [],
        "follow_ups": [],
        "error": False,
    }


# -------------------------------------------------------
# MACHINE NAME → ID RESOLUTION
# -------------------------------------------------------

def _validate_machine_existence(function_name, arguments):
    """
    Validate that every machine ID already present in arguments actually
    exists in the dataset.

    Returns an error message string if any machine ID is invalid, or None
    if all provided machine IDs are valid (or no machine ID was supplied yet).

    This MUST be called immediately after machine resolution, before asking
    for any other missing parameters.
    """
    resolver = get_resolver()
    valid_machines = resolver.all_machines()
    valid_ids = {m["machine_id"] for m in valid_machines}
    machine_param_names = [p for p in REQUIRED_PARAMS.get(function_name, []) if p in MACHINE_PARAMS]

    for param in machine_param_names:
        raw_val = arguments.get(param)
        if not raw_val:
            continue  # not yet supplied — will be asked for later

        mid = str(raw_val).upper()
        if mid not in valid_ids:
            if re.match(r"^M[A-Z0-9]*\d+[A-Z0-9]*$", mid):
                return f"Machine {raw_val} does not exist in the database."
            return f"Machine '{raw_val}' does not exist in the database."
            # Build a readable list of valid machines
            valid_list = "\n".join(
                f"  • {m['machine_id']} — {m['machine_name']}"
                for m in sorted(valid_machines, key=lambda m: m["machine_id"])
            )
            # Distinguish between an ID-like input and a name-like input
            import re as _re
            if _re.match(r"^M\d+$", mid):
                intro = f'Machine ID "{raw_val}" was not found in the database.'
            else:
                intro = f'Machine "{raw_val}" was not found in the database.'

            return (
                f"{intro}\n\n"
                f"Available machines:\n{valid_list}\n\n"
                "Please provide a valid Machine ID or Machine Name."
            )

    return None


def _resolve_machine_params(function_name, arguments, user_query):
    """
    For each machine param in arguments that looks like a name (not an ID),
    resolve it to a machine ID.

    Returns (resolved_arguments, ambiguity_error_message | None).
    The error message is set when the user typed a partial name matching
    multiple machines — we surface the choices and ask them to pick.
    """
    resolver = get_resolver()
    resolved = dict(arguments)
    machine_param_names = [p for p in REQUIRED_PARAMS.get(function_name, []) if p in MACHINE_PARAMS]

    missing_params = [p for p in machine_param_names if not resolved.get(p)]
    if missing_params:
        mentions = extract_machine_mentions(user_query, max_count=len(missing_params))
        for param, mention in zip(missing_params, mentions):
            resolved[param] = mention

    # Also try to find machine names mentioned in the raw query for params that are still null
    for param in machine_param_names:
        raw_val = resolved.get(param)
        if not raw_val:
            continue

        # Already a valid machine ID?
        if re.match(r"^M\d{3}$", str(raw_val), re.IGNORECASE):
            resolved[param] = raw_val.upper()
            continue

        # Try resolving name → ID
        machine_id, candidates = resolver.id_from_name_or_id(str(raw_val))
        if machine_id:
            resolved[param] = machine_id
        elif candidates:
            resolved[param] = None
            names = "\n".join(
                f"{idx}. {c['machine_name']} ({c['machine_id']})"
                for idx, c in enumerate(candidates, start=1)
            )
            return resolved, (
                f"I found multiple machines matching **{raw_val}**. "
                f"Please select one:\n\n{names}"
            )
        else:
            # Unrecognised name — keep the raw value so existence check can
            # report a useful error message instead of silently clearing it.
            # _validate_machine_existence will catch this below.
            pass

    return resolved, None


# -------------------------------------------------------
# DATE RESOLUTION FROM QUERY
# -------------------------------------------------------

def _resolve_dates_from_query(user_query, arguments, db_range):
    """
    Resolve dates from the user's query.

    Priority:
    1. Natural language dates (April, May, April to May, Complete Dataset)
       ALWAYS override any partial or incorrect dates extracted by the LLM.

    2. Explicit dates (2026-04-01, 01/04/2026)

    3. Existing arguments (only if nothing new was found)
    """

    args = dict(arguments)

    # --------------------------------------------------
    # Priority 1 : Natural language dates
    # --------------------------------------------------
    resolved = resolve_dates(
        user_query,
        db_range["min_date"],
        db_range["max_date"]
    )

    if resolved:
        # IMPORTANT:
        # Replace BOTH dates completely.
        # Never merge with partially extracted dates.
        args["start_date"] = resolved["start_date"]
        args["end_date"] = resolved["end_date"]
        return args

    # --------------------------------------------------
    # Priority 2 : Explicit dates
    # --------------------------------------------------
    explicit_dates = _extract_explicit_dates(user_query)

    if len(explicit_dates) == 2:
        args["start_date"] = explicit_dates[0]
        args["end_date"] = explicit_dates[1]

    elif len(explicit_dates) == 1:
        args["start_date"] = explicit_dates[0]
        args["end_date"] = explicit_dates[0]

    return args


# -------------------------------------------------------
# PARAMETER VALIDATION (returns error string or None)
# -------------------------------------------------------

def _validate_params(arguments, db_range):
    """
    Validate all provided parameters in priority order per spec:
    1. Date format
    2. Natural language conversion (already done before this call)
    3. Database date range
    4. Logical date order
    5. Machine ID validity
    Returns an error message string, or None if all valid.
    """
    start = arguments.get("start_date")
    end = arguments.get("end_date")

    if start and end:
        error = validate_date_range(start, end, db_range["min_date"], db_range["max_date"])
        if error:
            return error

    return None


# -------------------------------------------------------
# LLM SUMMARY
# -------------------------------------------------------

_SUMMARY_MAX_ROWS = 5


def _trim_for_summary(data):
    if not isinstance(data, dict):
        return data
    trimmed = {}
    for key, value in data.items():
        if isinstance(value, list) and len(value) > _SUMMARY_MAX_ROWS:
            trimmed[key] = value[:_SUMMARY_MAX_ROWS]
        else:
            trimmed[key] = value
    return trimmed


def generate_summary(function_name, result_data):
    """Ask LLM to summarise the analytics result in plain English."""
    try:
        compact = _trim_for_summary(result_data)
        prompt = f"""You are a manufacturing analytics assistant.
Summarize the following {function_name} result in 2-3 clear, concise sentences.
Focus on the most important insights. Be specific with numbers.

Result:
{compact}

Summary:"""
        return ask_llm(prompt)
    except Exception:
        return "Analysis complete. See the data and charts below for details."


# -------------------------------------------------------
# MAIN PROCESS FUNCTION
# -------------------------------------------------------

def process_query(user_query, chat_history=None, pending_state=None):
    """
    Main entry point called by app.py.

    Parameters
    ----------
    user_query   : str  — the latest user message
    chat_history : list — list of {role, content} dicts (used only for LLM context)
    pending_state: dict — {function, arguments} if we were waiting for params

    Returns
    -------
    dict with keys:
        intent         : str
        reply          : str  (always set)
        function_name  : str  (if executed)
        raw_data       : dict (if executed)
        summary        : str  (if executed)
        recommendations: list[str]
        follow_ups     : list[str]
        needs_params   : bool
        needs_machine  : bool
        needs_dates    : bool
        missing_machine_params : list[str]
        pending_state  : dict | None
        error          : bool
        arguments      : dict
    """
    chat_history = chat_history or []
    db_range = get_db_date_range()

    # ── HANDLE "complete range" shortcut from UI button ──────────────────
    q_lower = user_query.strip().lower()
    date_shortcut = None
    if any(kw in q_lower for kw in ["complete range", "all dates", "full range",
                                     "entire range", "all data", "complete database",
                                     "__complete_range__"]):
        date_shortcut = {
            "start_date": db_range["min_date"],
            "end_date": db_range["max_date"]
        }

    # ── IF WE HAVE PENDING STATE (waiting for missing params via UI) ──────
    if pending_state:
        # Req #14: Validate any date-like tokens the user just typed BEFORE merging
        date_format_error = detect_invalid_date_strings(user_query)
        if date_format_error:
            return {
                "intent": "manufacturing",
                "reply": f"⚠️ {date_format_error}",
                "needs_params": False,
                "needs_machine": False,
                "needs_dates": False,
                "missing_machine_params": [],
                "pending_state": pending_state,  # keep state so user can retry
                "arguments": pending_state.get("arguments", {}),
                "recommendations": [],
                "follow_ups": [],
                "error": True,
            }

        function_name = pending_state.get("function")
        # Start from stored arguments — NEVER overwrite stored non-null values.
        arguments = dict(pending_state.get("arguments", {}))

        # Apply date shortcut
        if date_shortcut:
            arguments.update(date_shortcut)
        else:
            # ── Merge machine from typed reply (fills only missing slots) ──────
            # Fixed regex: M\d{3} covers M001–M999 including M010
            machine_match = re.search(r'\b(M\d{3})\b', user_query, re.IGNORECASE)
            date_matches = re.findall(r'\b(\d{4}-\d{2}-\d{2})\b', user_query)

            if machine_match:
                mid = machine_match.group(1).upper()
                if "machine_id" in REQUIRED_PARAMS.get(function_name, []) and not arguments.get("machine_id"):
                    arguments["machine_id"] = mid
                elif "machine1" in REQUIRED_PARAMS.get(function_name, []) and not arguments.get("machine1"):
                    arguments["machine1"] = mid
                elif "machine2" in REQUIRED_PARAMS.get(function_name, []) and not arguments.get("machine2"):
                    arguments["machine2"] = mid
            else:
                # Try resolving machine name typed by user
                resolver = get_resolver()
                machine_id, candidates = resolver.id_from_name_or_id(user_query.strip())
                if machine_id:
                    if "machine_id" in REQUIRED_PARAMS.get(function_name, []) and not arguments.get("machine_id"):
                        arguments["machine_id"] = machine_id
                    elif "machine1" in REQUIRED_PARAMS.get(function_name, []) and not arguments.get("machine1"):
                        arguments["machine1"] = machine_id
                    elif "machine2" in REQUIRED_PARAMS.get(function_name, []) and not arguments.get("machine2"):
                        arguments["machine2"] = machine_id
                elif candidates:
                    names = "\n".join(f"• {c['machine_name']}" for c in candidates)
                    return _needs_params_response(
                        function_name, arguments,
                        get_missing_machine_params(function_name, arguments),
                        get_missing_date_params(function_name, arguments),
                        override_reply=f"Multiple machines match your input. Please select one:\n\n{names}"
                    )

            # ── Merge dates from typed reply — only when dates are missing ──────
            # RULE: if both dates are already stored, never overwrite them.
            already_has_dates = arguments.get("start_date") and arguments.get("end_date")
            if not already_has_dates:
                arguments = _resolve_dates_from_query(user_query, arguments, db_range)

                if date_matches:
                    if not arguments.get("start_date"):
                        arguments["start_date"] = date_matches[0]
                    if len(date_matches) >= 2 and not arguments.get("end_date"):
                        arguments["end_date"] = date_matches[1]
                    elif len(date_matches) == 1 and not arguments.get("end_date"):
                        arguments["end_date"] = date_matches[0]

        # Resolve machine names → IDs
        arguments, ambiguity_error = _resolve_machine_params(function_name, arguments, user_query)
        if ambiguity_error:
            return _needs_params_response(
                function_name, arguments,
                get_missing_machine_params(function_name, arguments),
                get_missing_date_params(function_name, arguments),
                override_reply=ambiguity_error
            )

        # ── MACHINE EXISTENCE CHECK (before asking for any other params) ──
        machine_error = _validate_machine_existence(function_name, arguments)
        if machine_error:
            return {
                "intent": "manufacturing",
                "reply": f"⚠️ {machine_error}",
                "needs_params": False,
                "needs_machine": False,
                "needs_dates": False,
                "missing_machine_params": [],
                "pending_state": None,
                "arguments": arguments,
                "recommendations": [],
                "follow_ups": [],
                "error": True,
            }

        # Validate before asking for more params
        validation_error = _validate_params(arguments, db_range)
        if validation_error:
            return {
                "intent": "manufacturing",
                "reply": f"⚠️ {validation_error}",
                "needs_params": False,
                "needs_machine": False,
                "needs_dates": False,
                "missing_machine_params": [],
                "pending_state": None,
                "arguments": arguments,
                "recommendations": [],
                "follow_ups": [],
                "error": True,
            }

        # Check what's still missing
        missing_machine = get_missing_machine_params(function_name, arguments)
        missing_dates = get_missing_date_params(function_name, arguments)
        missing_all = get_missing_params(function_name, arguments)

        if missing_all:
            return _needs_params_response(function_name, arguments, missing_machine, missing_dates)

        # Guard: same machine selected for both comparison slots
        same_machine_error = _check_same_machine(function_name, arguments)
        if same_machine_error:
            return same_machine_error

        return _execute_and_respond(function_name, arguments)

    # ── FRESH QUERY ───────────────────────────────────────────────────────
    # Req #14: Validate any date-like tokens in the raw query BEFORE anything else.
    date_format_error = detect_invalid_date_strings(user_query)
    if date_format_error:
        return {
            "intent": "manufacturing",
            "reply": f"⚠️ {date_format_error}",
            "needs_params": False,
            "needs_machine": False,
            "needs_dates": False,
            "missing_machine_params": [],
            "pending_state": None,
            "arguments": {},
            "recommendations": [],
            "follow_ups": [],
            "error": True,
        }

    selection = select_function(user_query, chat_history)
    intent = selection.get("intent")

    print(f"\nUSER QUERY:\n{user_query}")
    print(f"\nINTENT:\n{intent}")

    if intent in ("conversational", "gibberish", "incomplete", "out_of_scope"):
        _log_function_selection(None, reason=f"Intent classified as '{intent}' — no backend function needed.")
        return {
            "intent": intent,
            "reply": selection["reply"],
            "needs_params": False,
            "needs_machine": False,
            "needs_dates": False,
            "missing_machine_params": [],
            "pending_state": None,
            "arguments": {},
            "recommendations": [],
            "follow_ups": [],
            "error": False
        }

    # Manufacturing intent
    function_name = selection.get("function")
    arguments = selection.get("arguments", {})
    extracted_arguments = dict(arguments)

    print(f"\nSELECTED FUNCTION:\n{function_name}")
    print(f"\nEXTRACTED PARAMETERS (raw):\n{arguments}")

    if not function_name or function_name not in REQUIRED_PARAMS:
        _log_function_selection(None, reason="Function name missing or not recognised in REQUIRED_PARAMS.")
        return {
            "intent": "gibberish",
            "reply": GIBBERISH_REPLY,
            "needs_params": False,
            "needs_machine": False,
            "needs_dates": False,
            "missing_machine_params": [],
            "pending_state": None,
            "arguments": {},
            "recommendations": [],
            "follow_ups": [],
            "error": False
        }

    # Apply date shortcut if present
    if date_shortcut:
        arguments.update(date_shortcut)

    # Resolve machine names → IDs
    arguments, ambiguity_error = _resolve_machine_params(function_name, arguments, user_query)
    if ambiguity_error:
        missing_machine = get_missing_machine_params(function_name, arguments)
        missing_dates = get_missing_date_params(function_name, arguments)
        return _needs_params_response(
            function_name, arguments, missing_machine, missing_dates,
            override_reply=ambiguity_error
        )

    # ── MACHINE EXISTENCE CHECK (before asking for dates or any other params) ──
    machine_error = _validate_machine_existence(function_name, arguments)
    if machine_error:
        _log_pipeline(
            user_query, intent, function_name, extracted_arguments,
            arguments, "invalid machine", [], None, None, machine_error
        )
        return {
            "intent": "manufacturing",
            "reply": f"⚠️ {machine_error}",
            "needs_params": False,
            "needs_machine": False,
            "needs_dates": False,
            "missing_machine_params": [],
            "pending_state": None,
            "arguments": arguments,
            "recommendations": [],
            "follow_ups": [],
            "error": True,
        }

    # Resolve natural language dates from query
    arguments = _resolve_dates_from_query(user_query, arguments, db_range)

    print(f"\nEXTRACTED PARAMETERS (resolved):\n{arguments}")

    if _requires_scope_selection(function_name, user_query, arguments):
        return _scope_selection_response(function_name, arguments)

    # VALIDATION PRIORITY (spec §2):
    # 1+2+3+4. Validate dates (format, range, logical order) BEFORE asking for missing params
    validation_error = _validate_params(arguments, db_range)
    if validation_error:
        _log_pipeline(
            user_query, intent, function_name, extracted_arguments,
            arguments, "invalid parameters", [], None, None, validation_error
        )
        return {
            "intent": "manufacturing",
            "reply": f"⚠️ {validation_error}",
            "needs_params": False,
            "needs_machine": False,
            "needs_dates": False,
            "missing_machine_params": [],
            "pending_state": None,
            "arguments": arguments,
            "recommendations": [],
            "follow_ups": [],
            "error": True,
        }

    # 5-8. Ask only for remaining missing parameters
    missing_machine = get_missing_machine_params(function_name, arguments)
    missing_dates = get_missing_date_params(function_name, arguments)
    missing_all = get_missing_params(function_name, arguments)

    print(f"\nMISSING PARAMETERS:\n{missing_all}")

    if missing_all:
        _log_pipeline(
            user_query, intent, function_name, extracted_arguments,
            arguments, "valid", missing_all, None, None, None
        )
        return _needs_params_response(function_name, arguments, missing_machine, missing_dates)

    # Guard: same machine selected for both comparison slots
    same_machine_error = _check_same_machine(function_name, arguments)
    if same_machine_error:
        return same_machine_error

    _log_pipeline(
        user_query, intent, function_name, extracted_arguments,
        arguments, "valid", [], function_name, None, None
    )
    return _execute_and_respond(function_name, arguments)


# -------------------------------------------------------
# NEEDS PARAMS RESPONSE
# -------------------------------------------------------

def _check_same_machine(function_name, arguments):
    """Return an error response if machine1 and machine2 resolve to the same ID."""
    if function_name == "compare_machine_analytics":
        m1 = arguments.get("machine1")
        m2 = arguments.get("machine2")
        if m1 and m2 and m1 == m2:
            return {
                "intent": "manufacturing",
                "reply": (
                    "You selected the same machine for both comparison inputs. "
                    "Please choose two different machines."
                ),
                "needs_params": True,
                "needs_machine": True,
                "needs_dates": False,
                "missing_machine_params": ["machine1", "machine2"],
                "pending_state": None,
                "arguments": arguments,
                "recommendations": [],
                "follow_ups": [],
                "error": False,
            }
    return None


def _needs_params_response(function_name, arguments, missing_machine, missing_dates, override_reply=None):
    """Build a response indicating which UI controls to show."""
    needs_machine = len(missing_machine) > 0
    needs_dates = len(missing_dates) > 0

    if override_reply:
        msg = override_reply
    else:
        parts = []
        if needs_machine:
            if "machine1" in missing_machine and "machine2" in missing_machine:
                parts.append("Please select both machines to compare.")
            elif "machine1" in missing_machine:
                parts.append("Please select the first machine.")
            elif "machine2" in missing_machine:
                parts.append("Please select the second machine.")
            else:
                parts.append("Please provide Machine ID or Machine Name.")
        if needs_dates:
            if "start_date" in missing_dates and "end_date" in missing_dates:
                parts.append("Please provide Start Date and End Date.")
            elif "start_date" in missing_dates:
                parts.append("Please provide Start Date.")
            elif "end_date" in missing_dates:
                parts.append("Please provide End Date.")
        msg = " ".join(parts) if parts else "Please provide the missing information."

    return {
        "intent": "manufacturing",
        "reply": msg,
        "needs_params": True,
        "needs_machine": needs_machine,
        "needs_dates": needs_dates,
        "missing_machine_params": missing_machine,
        "pending_state": {"function": function_name, "arguments": arguments},
        "arguments": arguments,
        "recommendations": [],
        "follow_ups": [],
        "error": False
    }


# -------------------------------------------------------
# EXECUTE + BUILD RESPONSE
# -------------------------------------------------------

def _execute_and_respond(function_name, arguments):
    missing_machine = get_missing_machine_params(function_name, arguments)
    missing_dates = get_missing_date_params(function_name, arguments)
    missing_all = get_missing_params(function_name, arguments)
    if missing_all:
        return _needs_params_response(function_name, arguments, missing_machine, missing_dates)

    db_range = get_db_date_range()
    validation_error = _validate_params(arguments, db_range)
    if validation_error:
        return {
            "intent": "manufacturing",
            "reply": f"⚠️ {validation_error}",
            "needs_params": False,
            "needs_machine": False,
            "needs_dates": False,
            "missing_machine_params": [],
            "pending_state": None,
            "arguments": arguments,
            "recommendations": [],
            "follow_ups": [],
            "error": True,
        }

    machine_error = _validate_machine_existence(function_name, arguments)
    if machine_error:
        return {
            "intent": "manufacturing",
            "reply": f"⚠️ {machine_error}",
            "needs_params": False,
            "needs_machine": False,
            "needs_dates": False,
            "missing_machine_params": [],
            "pending_state": None,
            "arguments": arguments,
            "recommendations": [],
            "follow_ups": [],
            "error": True,
        }
    # Req #13 — log selected function and parameters to console before execution
    _log_function_selection(function_name, arguments)

    start = time.time()
    result = execute_tool(function_name, arguments)
    elapsed = time.time() - start

    print(f"\nEXECUTION TIME:\n{elapsed:.2f}s")

    if result.get("status") == "error":
        print(f"\nERRORS:\n{result.get('message')}")
        return {
            "intent": "manufacturing",
            "reply": f"⚠️ {result.get('message', 'Analysis failed. Please try again.')}",
            "needs_params": False,
            "needs_machine": False,
            "needs_dates": False,
            "missing_machine_params": [],
            "pending_state": None,
            "function_name": function_name,
            "raw_data": result,
            "summary": "",
            "recommendations": [],
            "follow_ups": [],
            "arguments": arguments,
            "error": True
        }

    # Enrich raw_data with display names for readability
    result = _enrich_with_display_names(result)

    summary = generate_summary(function_name, result.get("data", {}))
    recs = RECOMMENDATIONS.get(function_name, [])
    follow_ups = FOLLOW_UPS.get(function_name, [])

    return {
        "intent": "manufacturing",
        "reply": summary,
        "needs_params": False,
        "needs_machine": False,
        "needs_dates": False,
        "missing_machine_params": [],
        "pending_state": None,
        "function_name": function_name,
        "raw_data": result,
        "summary": summary,
        "recommendations": recs,
        "follow_ups": follow_ups,
        "arguments": arguments,
        "error": False
    }


def _enrich_with_display_names(result):
    """
    Add machine_display_name fields alongside machine_id in result data
    for human-readable reports: 'CNC Machine 1 (M001)'.
    """
    resolver = get_resolver()
    data = result.get("data")
    if not data:
        return result

    def _enrich_record(record):
        if not isinstance(record, dict):
            return record
        enriched = dict(record)
        for key in ("machine_id", "machine1", "machine2"):
            if key in enriched and enriched[key]:
                mid = enriched[key]
                display_key = key.replace("machine", "machine_display").replace("_id", "_name")
                if display_key == "machine_display":
                    display_key = "machine_display_name"
                enriched[display_key] = resolver.get_display_name(mid)
        return enriched

    if isinstance(data, dict):
        # Enrich top-level machine fields
        data = _enrich_record(data)
        # Enrich nested lists (machines, daily_data, etc.)
        for key, val in data.items():
            if isinstance(val, list):
                data[key] = [_enrich_record(r) for r in val]
        result = dict(result)
        result["data"] = data
    elif isinstance(data, list):
        result = dict(result)
        result["data"] = [_enrich_record(r) for r in data]

    return result
