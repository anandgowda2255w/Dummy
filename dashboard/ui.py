import datetime
import sqlite3

import streamlit as st

from dashboard.charts import render_chart
from llm.machine_resolver import get_resolver

# Import param metadata from assistant for Run Analysis visibility logic (Req #12)
from llm.assistant import REQUIRED_PARAMS, MACHINE_PARAMS, DATE_PARAMS


# =====================================================
# FUNCTION CLASSIFICATION
# =====================================================

SINGLE_MACHINE_FUNCTIONS = {
    "calculate_oee",
    "get_machine_downtime",
    "get_machine_rejection",
    "get_machine_production_summary",
    "get_machine_maintenance_recommendation",
}

COMPARE_FUNCTIONS = {
    "compare_machine_analytics",
}

PLANT_FUNCTIONS = {
    "get_downtime_analytics",
    "get_rejection_analytics",
    "get_production_summary",
    "get_plant_production_summary",
    "get_maintenance_recommendation",
}

# Maps selection_type → (machine-wise function, plant-wide function, label)
AMBIGUOUS_FUNCTION_MAP = {
    "downtime": {
        "machine": "get_machine_downtime",
        "plant":   "get_downtime_analytics",
        "options": ["Machine-wise Downtime", "Plant-wide Downtime"],
    },
    "rejection": {
        "machine": "get_machine_rejection",
        "plant":   "get_rejection_analytics",
        "options": ["Machine-wise Rejection", "Plant-wide Rejection"],
    },
    "production": {
        "machine": "get_machine_production_summary",
        "plant":   "get_production_summary",
        "options": ["Machine-wise Production", "Plant-wide Production"],
    },
}


# =====================================================
# DATABASE STATUS
# =====================================================

def check_db_status():
    try:
        conn = sqlite3.connect("database/manufacturing.db")
        conn.execute("SELECT 1")
        conn.close()
        return True
    except Exception:
        return False


# =====================================================
# ANALYSIS LABEL
# =====================================================

def analysis_label(function_name, arguments):
    labels = {
        "calculate_oee":                          "OEE Analysis",
        "get_machine_downtime":                   "Machine Downtime",
        "get_downtime_analytics":                 "Plant Downtime",
        "get_machine_rejection":                  "Machine Rejection",
        "get_rejection_analytics":                "Plant Rejection",
        "compare_machine_analytics":              "Machine Comparison",
        "get_production_summary":                 "Production Summary",
        "get_machine_production_summary":         "Machine Production",
        "get_maintenance_recommendation":         "Maintenance Recommendation",
        "get_machine_maintenance_recommendation": "Machine Maintenance Recommendation",
    }
    label = labels.get(function_name, function_name)
    machine = arguments.get("machine_id") or arguments.get("machine1")
    if machine:
        resolver = get_resolver()
        label += f" — {resolver.get_name(machine)}"
    return label


# =====================================================
# RECENT ANALYSIS
# =====================================================

def add_recent_analysis(label):
    recent = st.session_state.recent_analyses
    if label not in recent:
        recent.insert(0, label)
    st.session_state.recent_analyses = recent[:5]


# =====================================================
# UPDATE SESSION
# =====================================================

def update_session(response):
    fn   = response.get("function_name", "")
    args = response.get("arguments", {})

    machine = args.get("machine_id") or args.get("machine1")
    if machine:
        resolver = get_resolver()
        st.session_state.session_machine = resolver.get_display_name(machine)

    if args.get("start_date") and args.get("end_date"):
        st.session_state.session_date_range = (
            f"{args['start_date']} → {args['end_date']}"
        )

    label = analysis_label(fn, args)
    st.session_state.session_last_analysis = label
    add_recent_analysis(label)


# =====================================================
# ANALYSIS CARD
# =====================================================

def render_analysis_card(function_name, arguments, elapsed):
    labels = {
        "calculate_oee":                          "OEE Analysis",
        "get_machine_downtime":                   "Machine Downtime Analysis",
        "get_downtime_analytics":                 "Plant Downtime Analysis",
        "get_machine_rejection":                  "Machine Rejection Analysis",
        "get_rejection_analytics":                "Plant Rejection Analysis",
        "compare_machine_analytics":              "Machine Comparison",
        "get_production_summary":                 "Production Summary",
        "get_machine_production_summary":         "Machine Production",
        "get_maintenance_recommendation":         "Maintenance Recommendation",
        "get_machine_maintenance_recommendation": "Machine Maintenance Recommendation",
    }

    resolver = get_resolver()
    machine = (
        arguments.get("machine_id")
        or arguments.get("machine1")
    )
    machine = resolver.get_display_name(machine) if machine else "Plant"
    machine2 = arguments.get("machine2")
    if machine2:
        machine += f" vs {resolver.get_display_name(machine2)}"

    start = arguments.get("start_date", "-")
    end   = arguments.get("end_date",   "-")

    st.markdown(
        f"""
        <div class="analysis-card">
        <h4>📋 {labels.get(function_name, function_name)}</h4>
        <p>🤖 Machine: {machine}</p>
        <p>📅 Date Range: {start} → {end}</p>
        <p>⏱ Execution Time: {elapsed:.2f} sec</p>
        <p>🕒 Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


# =====================================================
# MAINTENANCE RECOMMENDATION CARDS
# =====================================================

def render_maintenance_cards(data):
    if not data:
        st.info("No maintenance recommendations found for the selected period.")
        return

    for rec in data:
        mid = rec.get("machine_id", "Unknown")
        machine = get_resolver().get_display_name(mid) if mid != "Unknown" else "Unknown"
        issue          = rec.get("issue",          "")
        recommendation = rec.get("recommendation", "")

        st.markdown(
            f"""
            <div class="analysis-card">
            <h4>🔧 {machine}</h4>
            <p>⚠️ <strong>Issue:</strong> {issue}</p>
            <p>✅ <strong>Recommendation:</strong> {recommendation}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )


# =====================================================
# ANALYSIS TYPE SELECTOR  (machine-wise vs plant-wide)
# =====================================================

def render_analysis_type_selector(pending_state, on_cancel=None):
    """
    Show radio buttons for ambiguous analysis types.
    Returns (chosen_function_name | None, cancelled: bool).

    Req #8: Cancel button is shown here too.
    """
    selection_type = pending_state.get("selection_type", "")
    mapping = AMBIGUOUS_FUNCTION_MAP.get(selection_type)

    if not mapping:
        return None, False

    options = mapping["options"]

    # Req #8 — Cancel during type selection
    cancel_col, _ = st.columns([1, 5])
    with cancel_col:
        ui_disabled = st.session_state.get("is_processing", False)
        if st.button(
            "⏹ Cancel",
            key=f"cancel_type_{selection_type}",
            type="secondary",
            disabled=ui_disabled,
        ):
            if on_cancel:
                on_cancel()
            return None, True

    # Use a session key so the radio persists across rerenders
    radio_key = f"analysis_type_{selection_type}"

    choice = st.radio(
        "Analysis type",
        options,
        index=None,               # nothing selected by default
        key=radio_key,
        label_visibility="collapsed",
    )

    if choice is None:
        return None, False

    # Map choice label → function name
    if choice == options[0]:     # machine-wise option (always first)
        return mapping["machine"], False
    else:                        # plant-wide option (always second)
        return mapping["plant"], False


# =====================================================
# PARAMETER COLLECTION
# =====================================================

def render_param_collector(pending_state, machines, db_range, on_cancel=None):
    """
    Render only the controls the current function requires.

    Single-machine  → machine_id + dates
    Comparison      → machine1 + machine2 + dates
    Plant           → dates only

    Req #8:  Stop/Cancel button is always shown during parameter collection.
    Req #12: Run Analysis button is hidden until ALL required parameters are
             filled and valid.
    """
    arguments     = dict(pending_state.get("arguments", {}))
    function_name = pending_state.get("function", "")
    # Build name→ID mapping for display; show names, store IDs
    name_to_id = {m["machine_name"]: m["machine_id"] for m in machines}
    machine_names = [m["machine_name"] for m in machines]

    # Issue #3: disable every control while the app is processing
    ui_disabled = st.session_state.get("is_processing", False)

    st.markdown('<div class="param-box">', unsafe_allow_html=True)

    # ── Req #8: Cancel button always visible during param collection ──────
    cancel_col, _ = st.columns([1, 5])
    with cancel_col:
        if st.button(
            "⏹ Cancel",
            key=f"cancel_param_{function_name}",
            type="secondary",
            disabled=ui_disabled,
        ):
            if on_cancel:
                on_cancel()
            return arguments, False, True   # (args, run, cancelled)

    # ── Single machine ────────────────────────────────────────────────────
    if function_name in SINGLE_MACHINE_FUNCTIONS:
        if not arguments.get("machine_id"):
            chosen_name = st.selectbox(
                "🤖 Machine",
                machine_names,
                index=None,
                placeholder="Select a machine…",
                key=f"sel_machine_{function_name}",
                disabled=ui_disabled,
            )
            if chosen_name:
                arguments["machine_id"] = name_to_id.get(chosen_name, chosen_name)

    # ── Two machines (comparison) ─────────────────────────────────────────
    elif function_name in COMPARE_FUNCTIONS:
        if not arguments.get("machine1"):
            chosen_name1 = st.selectbox(
                "🤖 Machine 1",
                machine_names,
                index=None,
                placeholder="Select Machine 1…",
                key=f"sel_machine1_{function_name}",
                disabled=ui_disabled,
            )
            if chosen_name1:
                arguments["machine1"] = name_to_id.get(chosen_name1, chosen_name1)
        if not arguments.get("machine2"):
            m1_name = next(
                (m["machine_name"] for m in machines if m["machine_id"] == arguments.get("machine1")),
                None,
            )
            available_names = [n for n in machine_names if n != m1_name]
            chosen_name2 = st.selectbox(
                "🤖 Machine 2",
                available_names,
                index=None,
                placeholder="Select Machine 2…",
                key=f"sel_machine2_{function_name}",
                disabled=ui_disabled,
            )
            if chosen_name2:
                arguments["machine2"] = name_to_id.get(chosen_name2, chosen_name2)

    # Plant functions: no machine selector at all

    # ── Date range (only shown if dates are still missing) ────────────────
    already_has_dates = arguments.get("start_date") and arguments.get("end_date")

    if not already_has_dates:
        st.markdown("### 📅 Select Date Range")

        col1, col2 = st.columns(2)

        with col1:
            if st.button(
                "🗓 Complete Range",
                width="stretch",
                key=f"btn_complete_{function_name}",
                disabled=ui_disabled,
            ):
                st.session_state.param_start_date  = db_range["min_date"]
                st.session_state.param_end_date    = db_range["max_date"]
                st.session_state.show_custom_dates = False
                st.rerun()

        with col2:
            if st.button(
                "🔧 Custom Range",
                width="stretch",
                key=f"btn_custom_{function_name}",
                disabled=ui_disabled,
            ):
                st.session_state.show_custom_dates = True
                st.rerun()

        if st.session_state.show_custom_dates:
            c1, c2 = st.columns(2)
            with c1:
                start_input = st.date_input(
                    "Start Date",
                    key=f"start_{function_name}",
                    disabled=ui_disabled,
                )
            with c2:
                end_input = st.date_input(
                    "End Date",
                    key=f"end_{function_name}",
                    disabled=ui_disabled,
                )

            if st.button(
                "Apply Date Range",
                key=f"apply_{function_name}",
                disabled=ui_disabled,
            ):
                if start_input > end_input:
                    st.error("Start date cannot be greater than end date.")
                else:
                    st.session_state.param_start_date  = start_input.isoformat()
                    st.session_state.param_end_date    = end_input.isoformat()
                    st.session_state.show_custom_dates = False
                    st.rerun()

    # Carry stored dates into arguments
    if st.session_state.param_start_date:
        arguments["start_date"] = st.session_state.param_start_date
    if st.session_state.param_end_date:
        arguments["end_date"] = st.session_state.param_end_date

    # Confirm selected range when both dates are present
    if arguments.get("start_date") and arguments.get("end_date"):
        st.success(f"📅 {arguments['start_date']} → {arguments['end_date']}")

    st.divider()

    # ── Req #12: Run Analysis only appears when ALL required params are filled ──
    required = REQUIRED_PARAMS.get(function_name, [])
    all_params_filled = all(bool(arguments.get(p)) for p in required)

    run = False
    if all_params_filled:
        run = st.button(
            "🚀 Run Analysis",
            width="stretch",
            key=f"run_{function_name}",
            disabled=ui_disabled,
        )
    # When params are still missing the button is simply not rendered.

    st.markdown("</div>", unsafe_allow_html=True)

    if run and not ui_disabled:
        # Validation guard
        missing = []

        if function_name in SINGLE_MACHINE_FUNCTIONS and not arguments.get("machine_id"):
            missing.append("machine")

        if function_name in COMPARE_FUNCTIONS:
            if not arguments.get("machine1"):
                missing.append("Machine 1")
            if not arguments.get("machine2"):
                missing.append("Machine 2")
            if (
                arguments.get("machine1")
                and arguments.get("machine2")
                and arguments["machine1"] == arguments["machine2"]
            ):
                st.error(
                    "You selected the same machine for both comparison inputs. "
                    "Please choose two different machines."
                )
                return arguments, False, False

        if not arguments.get("start_date") or not arguments.get("end_date"):
            missing.append("date range")

        if missing:
            st.error(f"Please provide: {', '.join(missing)} before running.")
            return arguments, False, False

        return arguments, True, False   # (args, run=True, cancelled=False)

    return arguments, False, False   # (args, run=False, cancelled=False)


# =====================================================
# RESULT DISPLAY
# =====================================================

def render_machine_maintenance_card(data, machine_id):
    """
    Render a single machine's maintenance recommendation card.
    Used when the user requested maintenance for a specific machine.
    """
    if not data:
        st.info(f"No maintenance issues found for {machine_id} in the selected period.")
        return

    resolver = get_resolver()
    display = resolver.get_display_name(machine_id)
    st.markdown(f"#### 🔧 Maintenance for {display}")
    for rec in data:
        issue          = rec.get("issue", "")
        recommendation = rec.get("recommendation", "")
        st.markdown(
            f"""
            <div class=\"analysis-card\">
            <p>⚠️ <strong>Issue:</strong> {issue}</p>
            <p>✅ <strong>Recommendation:</strong> {recommendation}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_analysis_result(response, elapsed=0, show_follow_ups: bool = True):
    """
    Render order: AI Summary → Analysis Card → Charts/Maintenance → Recommendations.
    Called ONLY from the chat history loop — never inline.

    Parameters
    ----------
    show_follow_ups : bool
        Retained for API compatibility but Follow-up Actions are permanently
        removed per spec §10.  Parameter is intentionally ignored.
    """
    function_name   = response.get("function_name", "")
    raw_data        = response.get("raw_data", {})
    summary         = response.get("summary", "")
    recommendations = response.get("recommendations", [])
    arguments       = response.get("arguments", {})

    # Error
    if response.get("error"):
        if summary:
            st.error(summary)
        return

    # No data
    if raw_data.get("status") == "error":
        st.warning("No data found for the selected criteria.")
        return

    # 1. AI Summary
    #if summary:
    #    st.info(summary)

    # 2. Analysis Card
    render_analysis_card(function_name, arguments, elapsed)

    # 3. Charts / Maintenance cards
    if function_name == "get_machine_maintenance_recommendation":
        machine_id = arguments.get("machine_id") or raw_data.get("machine_id", "")
        st.markdown("### 🔧 Maintenance Recommendation")
        render_machine_maintenance_card(raw_data.get("data", []), machine_id)

    elif function_name == "get_maintenance_recommendation":
        st.markdown("### 🔧 Maintenance Recommendations")
        render_maintenance_cards(raw_data.get("data", []))

    else:
        st.markdown("### 📊 Charts")
        render_chart(function_name, raw_data)

    # 4. Recommendations
    if recommendations:
        st.markdown("### 💡 Recommendations")
        for rec in recommendations:
            st.markdown(
                f'<span class="rec-pill">{rec}</span>',
                unsafe_allow_html=True,
            )

    # NOTE: Follow-up Actions section intentionally removed per spec §10.
    # No follow-up buttons are rendered regardless of show_follow_ups value.


# =====================================================
# SIDEBAR
# =====================================================

def render_sidebar(ollama_status, db_range, disabled: bool = False):
    """
    Render the sidebar.

    Parameters
    ----------
    disabled : bool
        When True (processing is active) all interactive controls in the
        sidebar are disabled so the user cannot trigger new actions.
    """
    with st.sidebar:
        st.markdown("## 🏭 Manufacturing AI")
        st.markdown("### 🖥 System Status")

        if check_db_status():
            st.success("Database Connected")
        else:
            st.error("Database Offline")

        if ollama_status:
            st.success("Ollama Running")
        else:
            st.error("Ollama Offline")

        if disabled:
            st.info("⏳ Processing — controls locked")

        st.divider()

        st.markdown("### 📌 Session Info")
        st.write("Current Machine:",    st.session_state.session_machine     or "-")
        st.write("Current Date Range:", st.session_state.session_date_range  or "-")
        st.write("Last Analysis:",      st.session_state.session_last_analysis or "-")

        st.divider()

        if st.session_state.recent_analyses:
            st.markdown("### 🕐 Recent Analyses")
            for item in st.session_state.recent_analyses:
                st.write("•", item)

        st.divider()

        st.markdown("### 📅 Database Range")
        st.write(f"{db_range['min_date']} → {db_range['max_date']}")

        st.divider()

        # Issue #3: disable sidebar button while processing
        if st.button("🗑 Clear Chat", width="stretch", disabled=disabled):
            st.session_state.messages              = []
            st.session_state.pending_state         = None
            st.session_state.recent_analyses       = []
            st.session_state.session_machine       = None
            st.session_state.session_date_range    = None
            st.session_state.session_last_analysis = None
            st.session_state.param_start_date      = None
            st.session_state.param_end_date        = None
            st.session_state.show_custom_dates     = False
            st.rerun()