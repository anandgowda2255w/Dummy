import uuid
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

CHART_BG   = "#0f1117"
PAPER_BG   = "#0f1117"
FONT_COLOR = "#e0e0e0"
GRID_COLOR = "#2a2d3e"

COLORS = [
    "#3b82f6",
    "#10b981",
    "#f59e0b",
    "#ef4444",
    "#8b5cf6",
    "#06b6d4",
]


# =====================================================
# SHARED LAYOUT HELPER
# =====================================================

def chart_layout(fig, title):
    fig.update_layout(
        title=title,
        template="plotly_dark",
        paper_bgcolor=PAPER_BG,
        plot_bgcolor=CHART_BG,
        font=dict(color=FONT_COLOR),
        height=420,
        margin=dict(l=30, r=30, t=60, b=30),
    )
    fig.update_xaxes(gridcolor=GRID_COLOR)
    fig.update_yaxes(gridcolor=GRID_COLOR)
    return fig


def _check_columns(df, required, chart_name):
    """Return True if all required columns are present, else warn and return False."""
    missing = [c for c in required if c not in df.columns]
    if missing:
        st.warning(f"{chart_name}: missing columns {missing}.")
        return False
    return True


# =====================================================
# OEE
# =====================================================

def render_oee_chart(data):
    """
    Bar chart: Availability / Performance / Quality / OEE (%).
    Data source: analytics calculate_oee → data dict.
    """
    if not data:
        st.warning("No chart data available.")
        return

    try:
        values = [
            data.get("availability", 0),
            data.get("performance", 0),
            data.get("quality", 0),
            data.get("oee", 0),
        ]
        labels = ["Availability", "Performance", "Quality", "OEE"]

        fig = px.bar(
            x=labels,
            y=values,
            color=labels,
            color_discrete_sequence=COLORS,
            labels={"x": "Metric", "y": "Percentage (%)"},
        )
        fig.update_yaxes(range=[0, 100])
        chart_layout(fig, "OEE Metrics (%)")
        st.plotly_chart(fig, width="stretch", key=f"oee_{uuid.uuid4()}")

    except Exception as e:
        st.warning(f"Unable to render OEE chart: {e}")


# =====================================================
# MACHINE DOWNTIME
# =====================================================

def render_machine_downtime(data):
    """
    Donut chart: downtime breakdown by reason for a single machine.
    Data source: data["downtime_by_reason"] → list of {reason, minutes}
    """
    reasons = data.get("downtime_by_reason", [])
    if not reasons:
        st.info("No downtime breakdown data available.")
        return

    try:
        df = pd.DataFrame(reasons)

        if df.empty:
            st.warning("No chart data available.")
            return

        if not _check_columns(df, ["reason", "minutes"], "Machine Downtime"):
            return

        fig = px.pie(
            df,
            names="reason",
            values="minutes",
            hole=0.45,
            color_discrete_sequence=COLORS,
        )
        chart_layout(fig, "Downtime by Reason (minutes)")
        st.plotly_chart(fig, width="stretch", key=f"downtime_{uuid.uuid4()}")

    except Exception as e:
        st.warning(f"Unable to render machine downtime chart: {e}")


# =====================================================
# PLANT DOWNTIME
# =====================================================

def render_plant_downtime(data):
    """
    Bar chart: downtime per machine, plant-wide.
    Analytics field: downtime_minutes  ← was incorrectly 'total_downtime'
    Data source: list of {machine_id, machine_name, downtime_minutes, ...}
    """
    if not data:
        st.warning("No chart data available.")
        return

    try:
        df = pd.DataFrame(data)

        if df.empty:
            st.warning("No chart data available.")
            return

        if not _check_columns(df, ["machine_id", "downtime_minutes"], "Plant Downtime"):
            return

        fig = px.bar(
            df,
            x="machine_id",
            y="downtime_minutes",          # ← corrected from total_downtime
            color="machine_id",
            color_discrete_sequence=COLORS,
            labels={"downtime_minutes": "Downtime (min)", "machine_id": "Machine"},
        )
        chart_layout(fig, "Plant Downtime by Machine (minutes)")
        st.plotly_chart(fig, width="stretch", key=f"plant_dt_{uuid.uuid4()}")

    except Exception as e:
        st.warning(f"Unable to render plant downtime chart: {e}")


# =====================================================
# MACHINE REJECTION
# =====================================================

def render_machine_rejection(data):
    """
    Grouped bar chart: daily production / rejection / good counts.
    Analytics daily_data fields: production, rejection, good
    ← was incorrectly using rejection_rate
    """
    rows = data.get("daily_data", [])
    if not rows:
        st.info("No daily rejection data available.")
        return

    try:
        df = pd.DataFrame(rows)

        if df.empty:
            st.warning("No chart data available.")
            return

        if not _check_columns(df, ["date", "production", "rejection", "good"], "Machine Rejection"):
            return

        fig = go.Figure()
        fig.add_trace(go.Bar(
            name="Production",
            x=df["date"],
            y=df["production"],
            marker_color=COLORS[0],
        ))
        fig.add_trace(go.Bar(
            name="Good",
            x=df["date"],
            y=df["good"],
            marker_color=COLORS[1],
        ))
        fig.add_trace(go.Bar(
            name="Rejection",
            x=df["date"],
            y=df["rejection"],
            marker_color=COLORS[3],
        ))
        fig.update_layout(barmode="group")
        chart_layout(fig, "Daily Production vs Rejection")
        st.plotly_chart(fig, width="stretch", key=f"rej_{uuid.uuid4()}")

    except Exception as e:
        st.warning(f"Unable to render machine rejection chart: {e}")


# =====================================================
# PLANT REJECTION
# =====================================================

def render_plant_rejection(data):
    """
    Bar chart: rejection_rate per machine, plant-wide.
    Analytics field: rejection_rate (already correct in analytics engine).
    """
    if not data:
        st.warning("No chart data available.")
        return

    try:
        df = pd.DataFrame(data)

        if df.empty:
            st.warning("No chart data available.")
            return

        if not _check_columns(df, ["machine_id", "rejection_rate"], "Plant Rejection"):
            return

        fig = px.bar(
            df,
            x="machine_id",
            y="rejection_rate",
            color="machine_id",
            color_discrete_sequence=COLORS,
            labels={"rejection_rate": "Rejection Rate (%)", "machine_id": "Machine"},
        )
        chart_layout(fig, "Plant Rejection Rate by Machine (%)")
        st.plotly_chart(fig, width="stretch", key=f"plant_rej_{uuid.uuid4()}")

    except Exception as e:
        st.warning(f"Unable to render plant rejection chart: {e}")


# =====================================================
# MACHINE COMPARISON
# =====================================================

def render_comparison(data):
    """
    Grouped bar chart: availability / performance / quality / OEE for two machines.
    Analytics fields: availability, performance, quality, oee.
    """
    if not data:
        st.warning("No chart data available.")
        return

    try:
        df = pd.DataFrame(data)

        if df.empty:
            st.warning("No chart data available.")
            return

        if not _check_columns(
            df,
            ["machine_id", "availability", "performance", "quality", "oee"],
            "Machine Comparison",
        ):
            return

        metrics = ["availability", "performance", "quality", "oee"]
        fig = go.Figure()

        for i, (_, row) in enumerate(df.iterrows()):
            fig.add_trace(go.Bar(
                name=row["machine_id"],
                x=metrics,
                y=[row["availability"], row["performance"], row["quality"], row["oee"]],
                marker_color=COLORS[i % len(COLORS)],
            ))

        fig.update_layout(barmode="group")
        chart_layout(fig, "Machine Comparison — OEE Metrics (%)")
        st.plotly_chart(fig, width="stretch", key=f"compare_{uuid.uuid4()}")

    except Exception as e:
        st.warning(f"Unable to render comparison chart: {e}")


# =====================================================
# PRODUCTION SUMMARY  (plant-wide)
# =====================================================

def render_production(data):
    """
    Bar chart: production count per machine, plant-wide.
    Analytics field: production  ← was incorrectly 'total_production'
    Data source: data["machines"] → list of {machine_id, production, ...}
    """
    rows = data.get("machines", [])
    if not rows:
        st.info("No production summary data available.")
        return

    try:
        df = pd.DataFrame(rows)

        if df.empty:
            st.warning("No chart data available.")
            return

        if not _check_columns(df, ["machine_id", "production"], "Production Summary"):
            return

        fig = px.bar(
            df,
            x="machine_id",
            y="production",                # ← corrected from total_production
            color="machine_id",
            color_discrete_sequence=COLORS,
            labels={"production": "Production Count", "machine_id": "Machine"},
        )
        chart_layout(fig, "Production Summary by Machine")
        st.plotly_chart(fig, width="stretch", key=f"prod_{uuid.uuid4()}")

    except Exception as e:
        st.warning(f"Unable to render production summary chart: {e}")


# =====================================================
# MACHINE PRODUCTION  (single machine, daily)
# =====================================================

def render_machine_production(data):
    """
    Line chart: daily production trend for a single machine.
    Analytics field: production  ← was incorrectly 'production_count'
    Data source: data["daily_data"] → list of {date, production, ...}
    """
    rows = data.get("daily_data", [])
    if not rows:
        st.info("No daily production data available.")
        return

    try:
        df = pd.DataFrame(rows)

        if df.empty:
            st.warning("No chart data available.")
            return

        if not _check_columns(df, ["date", "production"], "Machine Production"):
            return

        fig = px.line(
            df,
            x="date",
            y="production",                # ← corrected from production_count
            markers=True,
            labels={"production": "Production Count", "date": "Date"},
        )
        fig.update_traces(line_color=COLORS[0], marker_color=COLORS[1])
        chart_layout(fig, "Daily Production Trend")
        st.plotly_chart(fig, width="stretch", key=f"machine_prod_{uuid.uuid4()}")

    except Exception as e:
        st.warning(f"Unable to render machine production chart: {e}")


# =====================================================
# MAIN ROUTER
# =====================================================

def render_chart(function_name, raw_data):
    """
    Route to the correct renderer.
    Maintenance has no chart here — recommendation cards are
    rendered directly in ui.py via render_maintenance_cards().
    All renderers guard against empty DataFrames and missing columns.
    """
    data = raw_data.get("data", raw_data)

    try:
        if function_name == "calculate_oee":
            render_oee_chart(data)

        elif function_name == "get_machine_downtime":
            render_machine_downtime(data)

        elif function_name == "get_downtime_analytics":
            render_plant_downtime(data)

        elif function_name == "get_machine_rejection":
            render_machine_rejection(data)

        elif function_name == "get_rejection_analytics":
            render_plant_rejection(data)

        elif function_name == "compare_machine_analytics":
            render_comparison(data)

        elif function_name in ("get_production_summary", "get_plant_production_summary"):
            render_production(data)

        elif function_name == "get_machine_production_summary":
            render_machine_production(data)

        elif function_name == "get_maintenance_recommendation":
            # Intentionally empty — cards handled by ui.py
            pass

        else:
            st.info("No chart available for this analysis type.")

    except Exception as e:
        st.warning(f"Unable to render chart: {e}")