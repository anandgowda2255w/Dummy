"""
ambiguity.py

Intercepts ambiguous queries for Downtime / Rejection / Production
when the user has NOT specified machine-wise or plant-wide scope.

Runs BEFORE the LLM is called — if ambiguous, returns selection_required
immediately without touching the LLM or original process_query.

Place this file at:  llm/ambiguity.py
Import in app.py as: from llm.ambiguity import process_query
"""

import re

# ── Queries that are never ambiguous ─────────────────────────────────────────

UNAMBIGUOUS_PATTERNS = [
    r"\boee\b",
    r"\bcompare\b",
    r"\bcomparison\b",
    r"\bmaintenance\b",
    r"\brecommendation\b",
]

# ── Explicit machine scope signals ────────────────────────────────────────────

# Machine name keywords — covers spec names and common aliases
_MACHINE_NAME_KEYWORDS = [
    r"\bcnc\b", r"\blathe\b", r"\bhydraulic\b", r"\bprecision\b",
    r"\bdrill\b", r"\bpress\b", r"\bmilling\b",
    r"\bsurface\b", r"\bgrinder\b", r"\bgrinding\b",
    r"\bassembly\b",
]

MACHINE_SIGNALS = [
    r"\bm\d{3}\b",             # M001, m005, etc.
    r"\bcnc\s*\d+\b",
    r"\bdrill\s*\d+\b",
    r"\blathe\s*\d+\b",
    r"\bfor\s+m\d{3}\b",
    r"\bof\s+m\d{3}\b",
    r"\bspecific\s+machine\b",
    r"\bthis\s+machine\b",
    r"\bmachine-wise\b",
    r"\bmachinewise\b",
    r"\bmachine\s+production\b",      # "Machine Production Summary"
    r"\bmachine\s+downtime\b",        # "Machine Downtime"
    r"\bmachine\s+rejection\b",       # "Machine Rejection"
    r"\bmachine\s+maintenance\b",     # "Machine Maintenance"
    r"\bfor\s+a\s+machine\b",
    r"\bfor\s+the\s+machine\b",
] + _MACHINE_NAME_KEYWORDS

# ── Explicit plant scope signals ──────────────────────────────────────────────

PLANT_SIGNALS = [
    r"\ball machines?\b",
    r"\bplant.?wide\b",
    r"\bplant\b",
    r"\bfactory\b",
    r"\ball\b",
    r"\boverall\b",
    r"\bcomplete\s+dataset\b",
    r"\bentire\s+plant\b",
    r"\bwhole\s+plant\b",
    r"\bfactory\s+wide\b",
    r"\bevery machine\b",
    r"\bplant-wide\b",
    r"\bplant\s+production\b",        # "Plant Production Summary"
    r"\bplant\s+downtime\b",          # "Plant Downtime"
    r"\bplant\s+rejection\b",         # "Plant Rejection"
    r"\bplant\s+maintenance\b",       # "Plant Maintenance"
]

# ── Ambiguous keywords → selection_type ──────────────────────────────────────
# Order matters: more specific patterns first

AMBIGUOUS_PATTERNS = [
    (r"\bproduction\s+summary\b", "production"),
    (r"\bdowntime\b",             "downtime"),
    (r"\brejection\b",            "rejection"),
    (r"\bproduction\b",           "production"),
]

# ── Label map ─────────────────────────────────────────────────────────────────

LABELS = {
    "downtime":   "Downtime",
    "rejection":  "Rejection",
    "production": "Production",
}


def _has_match(patterns, text):
    return any(re.search(p, text, re.IGNORECASE) for p in patterns)


def _detect_ambiguous_type(query):
    """
    Return selection_type ('downtime'|'rejection'|'production') if the
    query is ambiguous — i.e. mentions one of those analyses but does NOT
    specify machine-wise or plant-wide scope.
    Returns None if the query is unambiguous or out of scope.
    """
    # Never ambiguous
    if _has_match(UNAMBIGUOUS_PATTERNS, query):
        return None

    # Already scoped by the user
    if _has_match(MACHINE_SIGNALS, query) or _has_match(PLANT_SIGNALS, query):
        return None

    # Match ambiguous keyword
    for pattern, selection_type in AMBIGUOUS_PATTERNS:
        if re.search(pattern, query, re.IGNORECASE):
            return selection_type

    return None


def _needs_selection_response(pending_state):
    """Build the standard needs_params response for selection_required state."""
    selection_type = pending_state.get("selection_type", "")
    label = LABELS.get(selection_type, "Analysis")
    return {
        "intent": "manufacturing",
        "reply": f"Please select the {label} analysis type.",
        "needs_params": True,
        "needs_machine": False,
        "needs_dates": False,
        "missing_machine_params": [],
        "pending_state": pending_state,
        "arguments": pending_state.get("arguments", {}),
        "recommendations": [],
        "follow_ups": [],
        "error": False,
    }


def _extract_arguments_from_query(user_query, db_range):
    """
    Extract whatever parameters can be resolved from the original query
    WITHOUT calling the LLM (fast, synchronous).

    Returns a dict of non-null arguments to seed into the pending state so
    that they are never asked for again.

    Extracts:
    - machine_id / machine1 / machine2 via the machine resolver
    - start_date / end_date via the date resolver
    """
    from llm.machine_resolver import get_resolver
    from llm.date_resolver import resolve_dates, _extract_explicit_dates

    args = {}

    # ── Date resolution ───────────────────────────────────────────────────
    resolved = resolve_dates(
        user_query,
        db_range["min_date"],
        db_range["max_date"],
    )
    if resolved:
        args["start_date"] = resolved["start_date"]
        args["end_date"] = resolved["end_date"]
    else:
        explicit = _extract_explicit_dates(user_query)
        if len(explicit) == 2:
            args["start_date"] = explicit[0]
            args["end_date"] = explicit[1]
        elif len(explicit) == 1:
            args["start_date"] = explicit[0]
            args["end_date"] = explicit[0]

    # ── Machine resolution ────────────────────────────────────────────────
    resolver = get_resolver()

    # Try exact ID patterns first (M001 … M010)
    machine_ids = re.findall(r'\bM\d{3}\b', user_query, re.IGNORECASE)
    if machine_ids:
        machine_ids = [mid.upper() for mid in machine_ids]
        if len(machine_ids) >= 2:
            args["machine1"] = machine_ids[0]
            args["machine2"] = machine_ids[1]
        elif len(machine_ids) == 1:
            args["machine_id"] = machine_ids[0]
    else:
        # Try name-based resolution
        machine_id, candidates = resolver.id_from_name_or_id(user_query.strip())
        if machine_id and not candidates:
            args["machine_id"] = machine_id

    return args


def process_query(user_query, chat_history=None, pending_state=None):
    """
    Ambiguity-aware wrapper around llm.assistant.process_query.

    Decision order:
      1. If pending_state has selection_required → keep showing selector.
      2. If query is ambiguous → extract params, return selection_required.
      3. Otherwise → delegate to original process_query unchanged.

    Importing original here (inside function) avoids circular-import
    issues regardless of how sys.path is configured on the host.
    """
    from llm.assistant import process_query as _original
    from analytics.analytics_engine import get_db_date_range

    chat_history = chat_history or []

    # ── 1. Already waiting for machine-wise vs plant-wide choice ─────────
    if pending_state and pending_state.get("selection_required"):
        return _needs_selection_response(pending_state)

    # ── 2. Detect ambiguity BEFORE calling the LLM ───────────────────────
    ambiguous_type = _detect_ambiguous_type(user_query)

    if ambiguous_type:
        # Extract whatever params are already present in the query so they
        # are preserved and never asked for again (parameter preservation).
        try:
            db_range = get_db_date_range()
        except Exception:
            db_range = {"min_date": "2026-01-01", "max_date": "2026-12-31"}

        extracted_args = _extract_arguments_from_query(user_query, db_range)

        new_pending = {
            "selection_required": True,
            "selection_type": ambiguous_type,
            "function": None,
            "arguments": extracted_args,   # ← preserved, not {}
        }
        return _needs_selection_response(new_pending)

    # ── 3. Not ambiguous — pass through to original assistant ────────────
    return _original(
        user_query=user_query,
        chat_history=chat_history,
        pending_state=pending_state,
    )
