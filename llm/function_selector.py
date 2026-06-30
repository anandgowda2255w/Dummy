import json
import re
from llm.llm_handler import ask_llm
from llm.date_resolver import _extract_explicit_dates
from llm.machine_resolver import get_resolver

# -------------------------------------------------------
# INTENT CLASSIFICATION — runs LOCALLY without LLM call
# -------------------------------------------------------

CONVERSATIONAL_PATTERNS = [
    r"^(hi|hello|hey|greetings|howdy)[\s!?.]*$",
    r"^(who are you|what are you|tell me about yourself)[\s?]*$",
    r"^(what can you do|what do you know|help|capabilities)[\s?]*$",
    r"^(thanks?|thank you|thx|cheers)[\s!.]*$",
    r"^(bye|goodbye|see you|exit|quit|ciao)[\s!.]*$",
    r"^(ok|okay|got it|sure|alright|great|nice|cool|wow|awesome)[\s!.]*$",
    r"^(yes|no|maybe|nope|yep|yeah)[\s!.]*$",
]

INCOMPLETE_PATTERNS = [
    r"^(give|show|tell|analyze|get|fetch|calculate|find|check|display|report)[\s!?.]*$",
]

MANUFACTURING_KEYWORDS = [
    # Analytics terms
    "oee", "downtime", "rejection", "production", "machine", "compare",
    "availability", "performance", "quality", "maintenance", "alert",
    "summary", "plant", "efficiency", "output",
    "throughput", "uptime", "defect", "scrap", "yield", "comparison",
    # Machine IDs
    "m001", "m002", "m003", "m004", "m005",
    "m006", "m007", "m008", "m009", "m010",
    # Machine name keywords (new spec names)
    "cnc", "lathe", "hydraulic", "precision", "drill", "press",
    "milling", "center", "surface", "grinder", "assembly", "line",
    # Synonyms per spec
    "breakdown", "stoppage", "idle", "failure",
    "equipment", "effectiveness", "service", "servicing", "repair",
    "inspection", "health", "reject", "report", "status",
    "overview", "manufacturing",
]

INTENT_FUNCTION_PATTERNS = [
    ("compare_machine_analytics", [
        r"\bcompare\b", r"\bcomparison\b", r"\bvs\b", r"\bversus\b",
    ]),
    ("calculate_oee", [
        r"\boee\b", r"\boverall\s+equipment\s+effectiveness\b",
        r"\bavailability\b", r"\bperformance\b", r"\bquality\b",
    ]),
    ("get_downtime_analytics", [
        r"\bdowntime\b", r"\bbreakdown\b", r"\bfailure\b",
        r"\bidle\b", r"\bstop(?:page|ped|s)?\b",
    ]),
    ("get_maintenance_recommendation", [
        r"\bmaintenance\b", r"\brecommendation\b", r"\bpreventive\b",
        r"\burgent\s+maintenance\b", r"\bmaintenance\s+schedule\b",
        r"\bservice\b", r"\bservicing\b", r"\brepair\b", r"\binspection\b",
    ]),
    ("get_production_summary", [
        r"\bproduction\b", r"\boutput\b", r"\bsummary\b",
    ]),
    ("get_rejection_analytics", [
        r"\brejection\b", r"\breject\b", r"\bscrap\b", r"\bdefect\b",
    ]),
]

OUT_OF_SCOPE_PATTERNS = [
    r"\bweather\b", r"\bjoke\b", r"\bcricket\s+match\b",
    r"\bwho\s+won\b", r"\bwhat\s+is\s+python\b", r"\bcooking\b",
    r"\brecipe\b", r"\bsports?\b", r"\bnews\b", r"\bstock\s+market\b",
]

OUT_OF_SCOPE_REPLY = (
    "I specialize in manufacturing analytics. I can help you with:\n\n"
    "• **OEE Analysis** — Overall Equipment Effectiveness\n"
    "• **Production Summary** — Machine or plant-wide output\n"
    "• **Downtime Analysis** — Breakdown and idle time\n"
    "• **Rejection Analysis** — Defect and scrap rates\n"
    "• **Machine Comparison** — Side-by-side performance\n"
    "• **Maintenance Recommendations** — Based on alerts and patterns\n\n"
    "Please ask about your manufacturing data!"
)


def classify_intent(user_query: str) -> str:
    """Returns: 'conversational' | 'incomplete' | 'manufacturing' | 'gibberish' | 'out_of_scope'"""
    q = user_query.strip().lower()

    for pat in OUT_OF_SCOPE_PATTERNS:
        if re.search(pat, q):
            return "out_of_scope"

    for pattern in CONVERSATIONAL_PATTERNS:
        if re.match(pattern, q, re.IGNORECASE):
            return "conversational"

    for pattern in INCOMPLETE_PATTERNS:
        if re.match(pattern, q, re.IGNORECASE):
            return "incomplete"

    for kw in MANUFACTURING_KEYWORDS:
        if kw in q:
            return "manufacturing"

    words = q.split()
    if len(words) <= 2:
        return "gibberish"

    if re.match(r"^[a-z0-9]{4,}$", q) and not any(kw in q for kw in MANUFACTURING_KEYWORDS):
        return "gibberish"

    return "manufacturing"


def get_conversational_reply(user_query: str) -> str:
    q = user_query.strip().lower()

    if re.match(r"^(hi|hello|hey|greetings|howdy)", q):
        return "Hi! I'm the AI Manufacturing Assistant. How can I help you today?"

    if re.match(r"^(who are you|what are you|tell me about yourself)", q):
        return (
            "I'm an AI Manufacturing Assistant that analyzes manufacturing data "
            "using AI-driven function calling. I connect to a live production database "
            "and use predefined backend tools to fetch insights."
        )

    if re.match(r"^(what can you do|help|capabilities)", q):
        return (
            "I can help you with:\n\n"
            "• **OEE Analysis** — Availability, Performance, Quality for any machine\n"
            "• **Downtime Analysis** — Plant-wide or machine-specific breakdown\n"
            "• **Rejection Analysis** — Defect rates across machines\n"
            "• **Production Summary** — Plant or machine output overview\n"
            "• **Machine Comparison** — Side-by-side metrics for two machines\n"
            "• **Maintenance Recommendations** — Based on alerts and downtime patterns\n\n"
            "You can use machine names like 'Hydraulic Press' or IDs like 'M009'.\n"
            "Just ask in plain English!"
        )

    if re.match(r"^(thanks?|thank you|thx|cheers)", q):
        return "You're welcome!"

    if re.match(r"^(bye|goodbye|see you|exit|quit|ciao)", q):
        return "Goodbye! 👋"

    if re.match(r"^(ok|okay|got it|sure|alright|great|nice|cool|wow|awesome|yes|no|nope|yep|yeah)", q):
        return "Got it! Feel free to ask anything about your manufacturing data."

    return "I'm here to help! Ask me about OEE, downtime, production, or machine comparisons."


GIBBERISH_REPLY = (
    "I couldn't understand your request.\n\n"
    "Try:\n"
    "• Calculate OEE for Hydraulic Press during April\n"
    "• Show downtime of CNC Lathe 1\n"
    "• Compare Milling Center and Assembly Line\n"
    "• Production summary for May\n"
    "• Maintenance recommendations"
)

INCOMPLETE_REPLY = (
    "What would you like me to analyze?\n\n"
    "Available:\n"
    "• OEE\n"
    "• Downtime\n"
    "• Rejection\n"
    "• Production Summary\n"
    "• Machine Comparison\n"
    "• Maintenance Recommendations"
)


# -------------------------------------------------------
# PARAMETER EXTRACTION via LLM (SINGLE call)
# -------------------------------------------------------

def extract_parameters(user_query: str, chat_history=None) -> dict | None:
    """
    Ask the LLM to extract function + parameters from the user query.
    Machine names are extracted as canonical IDs using the spec name table.
    Date expressions are left as null if not in YYYY-MM-DD — date_resolver handles them.
    """
    prompt = f"""You are a manufacturing AI assistant. Extract the correct function and parameters from the user query.

Available functions:
1. calculate_oee(machine_id, start_date, end_date) - OEE for ONE specific machine
2. get_downtime_analytics(start_date, end_date) - Downtime for ALL machines (plant-wide)
3. get_machine_downtime(machine_id, start_date, end_date) - Downtime for ONE specific machine
4. get_rejection_analytics(start_date, end_date) - Rejection for ALL machines
5. get_machine_rejection(machine_id, start_date, end_date) - Rejection for ONE machine
6. compare_machine_analytics(machine1, machine2, start_date, end_date) - Compare two machines
7. get_production_summary(start_date, end_date) - Production for ALL machines (plant-wide)
8. get_machine_production_summary(machine_id, start_date, end_date) - Production for ONE machine
9. get_maintenance_recommendation(start_date, end_date) - Maintenance recommendations for ALL machines (plant-wide)
10. get_machine_maintenance_recommendation(machine_id, start_date, end_date) - Maintenance recommendation for ONE specific machine

Known machines — accept any alias and output the machine ID:
- M001: CNC Lathe 1 (also: CNC Lathe 1, cnc lathe, cnc1)
- M002: CNC Lathe 2 (also: CNC Lathe 2, cnc2)
- M003: Hydraulic Lathe (also: hydraulic lathe, lathe 1)
- M004: Precision Lathe (also: precision lathe, lathe 2)
- M005: Drill Press 1 (also: drill press 1, drill 1)
- M006: Drill Press 2 (also: drill press 2, drill 2)
- M007: Milling Center (also: milling center, milling, mill)
- M008: Surface Grinder (also: surface grinder, grinder, grinding machine)
- M009: Hydraulic Press (also: hydraulic press, press, press machine)
- M010: Assembly Line (also: assembly line, assembly, assembly machine)

CRITICAL Rules:
- Return ONLY valid JSON, no markdown, no explanation, no backticks.
- Extract parameters ONLY from this exact user query.
- If a machine is mentioned by name, resolve it to the ID above and output that ID.
- If a machine is mentioned by ID (M001…M010), use that ID.
- If NO machine is mentioned, use plant-wide functions (no machine_id).
- Set unknown/missing parameters to null.
- Dates: only output YYYY-MM-DD for EXPLICITLY stated dates like "01/04/2026" → "2026-04-01".
  For month names like "April", "during May", or "complete dataset", set dates to null.
  The date resolver will handle all natural language dates.
- Synonyms: breakdown/stoppage/idle/failure=downtime; efficiency/effectiveness=oee;
  scrap/defect/reject=rejection; service/repair/inspection=maintenance.
- "Compare" → compare_machine_analytics with two machines.
- "OEE" or "efficiency" alone (no machine) → calculate_oee with null machine_id.
- "Downtime" alone → get_downtime_analytics.
- "Production" or "production summary" alone → get_production_summary.
- "Rejection" alone → get_rejection_analytics.
- "Maintenance" or "recommendations" WITH a specific machine → get_machine_maintenance_recommendation with that machine_id.
- "Maintenance" or "recommendations" WITHOUT a specific machine → get_maintenance_recommendation.

User query: {user_query}

Return JSON:
{{"function": "function_name", "arguments": {{"param": "value_or_null"}}}}"""

    try:
        response = ask_llm(prompt)
        response = response.replace("```json", "").replace("```", "").strip()
        match = re.search(r'\{.*\}', response, re.DOTALL)
        if match:
            return json.loads(match.group())
    except Exception:
        pass
    return None


# -------------------------------------------------------
# DETERMINISTIC FUNCTION SELECTION + PARAMETER EXTRACTION
# -------------------------------------------------------

MACHINE_STOPWORDS = {
    "oee", "overall", "equipment", "effectiveness", "analysis", "analytics",
    "calculate", "show", "give", "get", "find", "check", "display", "report",
    "of", "for", "from", "to", "between", "and", "during", "in", "on",
    "downtime", "breakdown", "failure", "idle", "stop", "stoppage",
    "maintenance", "recommendation", "preventive", "urgent", "schedule",
    "production", "output", "summary", "rejection", "reject", "scrap",
    "defect", "compare", "comparison", "vs", "versus", "machine",
    "start", "end", "date", "range",
}


def _detect_function_from_query(user_query: str) -> str | None:
    q = user_query.lower()
    for function_name, patterns in INTENT_FUNCTION_PATTERNS:
        if any(re.search(pattern, q, re.IGNORECASE) for pattern in patterns):
            return function_name
    return None


def _strip_dates(text: str) -> str:
    value = re.sub(r"\b\d{4}[-/]\d{1,2}[-/]\d{1,2}\b", " ", text)
    value = re.sub(r"\b\d{1,2}[-/]\d{1,2}[-/]\d{4}\b", " ", value)
    value = re.sub(
        r"\b(january|jan|february|feb|march|mar|april|apr|may|june|jun|july|jul|"
        r"august|aug|september|sep|sept|october|oct|november|nov|december|dec)\b",
        " ",
        value,
        flags=re.IGNORECASE,
    )
    return value


def _candidate_spans(user_query: str) -> list[str]:
    text = _strip_dates(user_query)
    spans: list[str] = []

    for match in re.finditer(
        r"\b(?:of|for|machine)\s+([A-Za-z][A-Za-z0-9]*(?:\s+[A-Za-z][A-Za-z0-9]*){0,3})",
        text,
        re.IGNORECASE,
    ):
        spans.append(match.group(1))

    cleaned_tokens = []
    for token in re.findall(r"\b[A-Za-z][A-Za-z0-9]*\b", text):
        if token.lower() not in MACHINE_STOPWORDS:
            cleaned_tokens.append(token)

    if cleaned_tokens:
        spans.append(" ".join(cleaned_tokens))

    return spans


def extract_machine_mentions(user_query: str, max_count: int = 2) -> list[str]:
    """
    Extract machine candidates from the query without inventing values.

    Order:
      1. Exact machine ID
      2. Regex ID-like candidate
      3. Exact machine name
      4. Case-insensitive name
      5. Partial machine-name match
      6. Raw name-like leftover candidate for validation
    """
    resolver = get_resolver()
    machines = resolver.all_machines()
    found: list[str] = []

    def add(value):
        if value and value not in found:
            found.append(value)

    exact_ids = {m["machine_id"] for m in machines}
    for match in re.finditer(r"\bM\d{3}\b", user_query, re.IGNORECASE):
        candidate = match.group(0).upper()
        if candidate in exact_ids:
            add(candidate)

    for match in re.finditer(r"\bM[A-Za-z0-9]*\d+[A-Za-z0-9]*\b", user_query, re.IGNORECASE):
        candidate = match.group(0).upper()
        if candidate not in exact_ids:
            add(candidate)

    text_l = user_query.lower()
    for machine in machines:
        if re.search(rf"\b{re.escape(machine['machine_name'].lower())}\b", text_l):
            add(machine["machine_id"])

    for machine in machines:
        if machine["machine_name"].lower() in text_l:
            add(machine["machine_id"])

    for span in _candidate_spans(user_query):
        machine_id, candidates = resolver.id_from_name_or_id(span)
        if machine_id:
            add(machine_id)
        elif len(candidates) == 1:
            add(candidates[0]["machine_name"])

    if not found:
        for span in _candidate_spans(user_query):
            words = [w for w in re.findall(r"\b[A-Za-z][A-Za-z0-9]*\b", span)
                     if w.lower() not in MACHINE_STOPWORDS]
            if words:
                add(" ".join(words))
                break

    return found[:max_count]


def _extract_dates_from_query(user_query: str) -> dict:
    dates = _extract_explicit_dates(user_query)
    if len(dates) >= 2:
        return {"start_date": dates[0], "end_date": dates[1]}
    if len(dates) == 1:
        return {"start_date": dates[0], "end_date": dates[0]}
    return {"start_date": None, "end_date": None}


def _deterministic_extract(user_query: str) -> dict | None:
    function_name = _detect_function_from_query(user_query)
    if not function_name:
        return None

    args = _extract_dates_from_query(user_query)
    machines = extract_machine_mentions(user_query, max_count=2)

    if function_name == "compare_machine_analytics":
        args["machine1"] = machines[0] if len(machines) >= 1 else None
        args["machine2"] = machines[1] if len(machines) >= 2 else None
    elif function_name in {
        "calculate_oee",
        "get_machine_downtime",
        "get_machine_rejection",
        "get_machine_production_summary",
        "get_machine_maintenance_recommendation",
    }:
        args["machine_id"] = machines[0] if machines else None
    elif machines:
        if function_name == "get_downtime_analytics":
            function_name = "get_machine_downtime"
            args["machine_id"] = machines[0]
        elif function_name == "get_rejection_analytics":
            function_name = "get_machine_rejection"
            args["machine_id"] = machines[0]
        elif function_name == "get_production_summary":
            function_name = "get_machine_production_summary"
            args["machine_id"] = machines[0]
        elif function_name == "get_maintenance_recommendation":
            function_name = "get_machine_maintenance_recommendation"
            args["machine_id"] = machines[0]

    return {"function": function_name, "arguments": args}


def select_function(user_query: str, chat_history=None) -> dict:
    """Full pipeline: classify → extract → return result dict."""
    intent = classify_intent(user_query)

    if intent == "conversational":
        return {"intent": "conversational", "reply": get_conversational_reply(user_query)}

    if intent == "incomplete":
        return {"intent": "incomplete", "reply": INCOMPLETE_REPLY}

    if intent == "out_of_scope":
        return {"intent": "out_of_scope", "reply": OUT_OF_SCOPE_REPLY}

    if intent == "gibberish":
        return {"intent": "gibberish", "reply": GIBBERISH_REPLY}

    # Manufacturing intent. Prefer deterministic rules so the user's analysis
    # type decides the backend function before any machine-name signal.
    parsed = _deterministic_extract(user_query)
    if not parsed:
        parsed = extract_parameters(user_query)
    if not parsed:
        return {"intent": "gibberish", "reply": GIBBERISH_REPLY}

    return {
        "intent": "manufacturing",
        "function": parsed.get("function"),
        "arguments": parsed.get("arguments", {}),
    }
