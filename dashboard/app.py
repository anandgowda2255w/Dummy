import os
import sys
import time
import threading
import streamlit as st

sys.path.append(
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..")
    )
)

from dashboard.styles import load_css
from dashboard.ui import (
    render_sidebar,
    render_param_collector,
    render_analysis_result,
    render_analysis_type_selector,
    update_session,
)
from llm.ambiguity import process_query          # ambiguity-aware wrapper
from llm.assistant import _execute_and_respond   # execution logic unchanged
from llm.llm_handler import check_ollama_status
from analytics.analytics_engine import get_db_date_range, get_all_machines

# =====================================================
# PAGE CONFIG
# =====================================================

st.set_page_config(
    page_title="AI Manufacturing Assistant",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(load_css(), unsafe_allow_html=True)

# =====================================================
# SESSION STATE
# =====================================================

DEFAULT_STATE = {
    "messages": [],
    "pending_state": None,
    "recent_analyses": [],
    "session_machine": None,
    "session_date_range": None,
    "session_last_analysis": None,
    "param_start_date": None,
    "param_end_date": None,
    "show_custom_dates": False,
    # ── Global processing state (Issue #6) ───────────
    "is_processing": False,
    "stop_requested": False,
}

for key, value in DEFAULT_STATE.items():
    if key not in st.session_state:
        st.session_state[key] = value


# =====================================================
# PROCESSING STATE HELPERS
# =====================================================

def _start_processing():
    """Enter processing state: lock UI, show stop button."""
    st.session_state.is_processing = True
    st.session_state.stop_requested = False


def _end_processing():
    """Leave processing state: unlock UI, hide stop button."""
    st.session_state.is_processing = False
    st.session_state.stop_requested = False


def _request_stop():
    """Called when the user clicks Stop."""
    st.session_state.stop_requested = True


# =====================================================
# USER INPUT HANDLER
# =====================================================

def handle_user_input(user_input, machines, db_range):
    """
    Process the user message and update session state.

    RULE: Never render anything inline here.
          All output renders exclusively from the
          `for msg in st.session_state.messages` loop.
    """
    # Guard: block concurrent requests (Issue #5)
    if st.session_state.is_processing:
        return

    _start_processing()

    with st.chat_message("assistant"):
        status_col, stop_col = st.columns([5, 1])
        with status_col:
            status = st.empty()
            status.info("🤖 Running analysis...")
        with stop_col:
            # Issue #2: Show Stop button while processing
            stop_placeholder = st.empty()
            stop_placeholder.button(
                "⏹ Stop",
                key="stop_btn_input",
                on_click=_request_stop,
                type="secondary",
            )

        start = time.time()

        try:
            # Check for stop before the (potentially slow) LLM call
            if st.session_state.stop_requested:
                status.empty()
                stop_placeholder.empty()
                _end_processing()
                return

            response = process_query(
                user_query=user_input,
                chat_history=st.session_state.messages[:-1],
                pending_state=st.session_state.pending_state,
            )
            elapsed = time.time() - start
            status.empty()
            stop_placeholder.empty()

            # If stop was requested while LLM was running, discard result
            if st.session_state.stop_requested:
                _end_processing()
                return

            pending = response.get("pending_state")

            # On error responses: always clear pending state so param
            # collector does not reopen (invalid machine / invalid date).
            if response.get("error"):
                st.session_state.pending_state = None
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": response.get("reply", ""),
                    "result": None,
                    "elapsed": elapsed,
                })
                _end_processing()
                st.rerun()
                return

            st.session_state.pending_state = pending

            # Conversational / gibberish / incomplete — plain text reply
            if not response.get("needs_params") and not response.get("function_name"):
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": response.get("reply", ""),
                    "result": None,
                    "elapsed": elapsed,
                })
                _end_processing()
                st.rerun()
                return

            # Needs params (including selection_required) — append prompt, rerun
            if response.get("needs_params"):
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": response.get("reply", ""),
                    "result": None,
                    "elapsed": elapsed,
                })
                _end_processing()
                st.rerun()
                return

            # Direct result (all params already present in query)
            update_session(response)
            st.session_state.messages.append({
                "role": "assistant",
                "content": response.get("reply", ""),
                "result": response if response.get("function_name") else None,
                "elapsed": elapsed,
            })
            _end_processing()
            st.rerun()

        except Exception as e:
            status.empty()
            stop_placeholder.empty()
            _end_processing()
            st.error(f"Unexpected error: {e}")


# =====================================================
# PENDING STATE HANDLER  (shown below chat history)
# =====================================================

def handle_pending_state(machines, db_range):
    """
    Render the appropriate UI for whatever is stored in pending_state.

    Two modes:
      1. selection_required=True  → show analysis-type radio buttons
      2. function present         → show parameter collector
    """
    pending = st.session_state.pending_state
    if not pending:
        return

    # Don't show param UI while processing (Issue #4 / #3)
    if st.session_state.is_processing:
        return

    with st.chat_message("assistant"):

        # ── MODE 1: user must pick machine-wise vs plant-wide ─────────────
        if pending.get("selection_required"):
            def _cancel_type_selection():
                st.session_state.pending_state    = None
                st.session_state.show_custom_dates = False
                st.session_state.param_start_date  = None
                st.session_state.param_end_date    = None

            chosen_function, cancelled = render_analysis_type_selector(
                pending, on_cancel=_cancel_type_selection
            )

            if cancelled:
                st.rerun()
                return

            if chosen_function:
                # Update pending state with the resolved function
                st.session_state.pending_state = {
                    "function": chosen_function,
                    "arguments": pending.get("arguments", {}),
                    "selection_required": False,
                }
                st.session_state.param_start_date = None
                st.session_state.param_end_date = None
                st.session_state.show_custom_dates = False
                st.rerun()
            return

        # ── MODE 2: function is known, collect remaining params ───────────
        if pending.get("function"):

            # Req #8: cancel callback resets all pending/param state
            def _cancel_param_collection():
                st.session_state.pending_state    = None
                st.session_state.show_custom_dates = False
                st.session_state.param_start_date  = None
                st.session_state.param_end_date    = None

            arguments, run, cancelled = render_param_collector(
                pending, machines, db_range, on_cancel=_cancel_param_collection
            )

            if cancelled:
                # on_cancel already updated session state — just rerun
                st.rerun()
                return

            if run:
                # Guard: block concurrent requests (Issue #5)
                if st.session_state.is_processing:
                    return

                _start_processing()
                function_name = pending["function"]

                try:
                    result = _execute_and_respond(function_name, arguments)
                finally:
                    _end_processing()

                st.session_state.pending_state = None
                st.session_state.show_custom_dates = False
                st.session_state.param_start_date = None
                st.session_state.param_end_date = None

                update_session(result)

                st.session_state.messages.append({
                    "role": "assistant",
                    "content": result.get("reply", ""),
                    "result": result,
                    "elapsed": 0,
                })
                st.rerun()


# =====================================================
# MAIN
# =====================================================

def main():
    ollama_status = check_ollama_status()

    try:
        db_range = get_db_date_range()
        machines = get_all_machines()
    except Exception:
        db_range = {"min_date": "2026-01-01", "max_date": "2026-12-31"}
        machines = []

    processing = st.session_state.is_processing

    render_sidebar(ollama_status, db_range, disabled=processing)

    st.title("🏭 AI Manufacturing Data Assistant")
    st.caption("AI-powered analytics using Function Calling + Ollama")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Machines", len(machines))
    with col2:
        st.metric("Production Logs", 600)
    with col3:
        st.metric("Analytics Functions", 9)
    with col4:
        st.metric("AI Status", "Active" if ollama_status else "Offline")

    st.divider()

    # =====================================
    # WELCOME
    # =====================================
    if not st.session_state.messages:
        st.markdown(
            """
            <div class="welcome-box">
            <h2>🏭 AI Manufacturing Data Assistant</h2>
            <p>Ask questions about:</p>
            <p>
            • OEE Analysis<br>
            • Downtime Analysis<br>
            • Production Summary<br>
            • Rejection Analysis<br>
            • Machine Comparison<br>
            • Maintenance Recommendation
            </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # =====================================
    # CHAT HISTORY — the ONLY render source
    # =====================================
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

            if msg["role"] == "assistant" and msg.get("result"):
                # Issue #4: hide follow-up buttons while processing
                render_analysis_result(
                    msg["result"],
                    msg.get("elapsed", 0),
                    show_follow_ups=not processing,
                )

    # =====================================
    # GLOBAL STOP BUTTON (Issue #2)
    # shown prominently above the input when processing
    # =====================================
    if processing:
        st.warning("⏳ Processing your request...")
        if st.button("⏹ Cancel Request", type="secondary", key="stop_btn_global"):
            _request_stop()
            _end_processing()
            st.rerun()

    # =====================================
    # PENDING STATE UI (below history)
    # =====================================
    handle_pending_state(machines, db_range)

    # =====================================
    # USER INPUT
    # =====================================
    # Issue #3: disable chat input while processing
    user_input = st.chat_input(
        "Ask about OEE, downtime, production...",
        disabled=processing,
    )

    if user_input and not processing:
        st.session_state.messages.append({"role": "user", "content": user_input})

        with st.chat_message("user"):
            st.markdown(user_input)

        handle_user_input(user_input, machines, db_range)


# =====================================================
# ENTRY
# =====================================================
if __name__ == "__main__":
    main()