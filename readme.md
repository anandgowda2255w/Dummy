# 🏭 AI Manufacturing Data Assistant

An AI-powered manufacturing analytics assistant built with **Function Calling**, **Ollama (qwen2.5:3b)**, **Streamlit**, **SQLite**, and **Plotly**. The AI never queries the database directly — it selects and calls predefined backend tools to fetch data, then generates natural-language insights.

---

## 📁 Project Structure

```
ai-manufacturing-assistant/
│
├── analytics/
│   └── analytics_engine.py       # All backend analytics functions
│
├── backend/
│   ├── database.py               # SQLite connection helper
│   ├── function_registry.py      # Maps function names → callables
│   ├── models.py
│   └── validators.py
│
├── dashboard/
│   └── app.py                    # Streamlit UI (main entry point)
│
├── database/
│   ├── manufacturing.db          # SQLite database (pre-populated)
│   ├── create_db.py
│   └── insert_data.py
│
├── llm/
│   ├── assistant.py              # Orchestrator: intent → params → execute → respond
│   ├── function_schemas.py       # Function definitions for LLM
│   ├── function_selector.py      # Intent classification + parameter extraction
│   ├── llm_handler.py            # Ollama API wrapper + status check
│   └── tool_executor.py          # Safely calls registered functions
│
├── requirements.txt
└── readme.md
```

---

## 🗄️ Database Schema

| Table              | Key Columns                                                                 |
|--------------------|-----------------------------------------------------------------------------|
| `machines`         | machine_id, machine_name, machine_type, location                            |
| `production_logs`  | date, machine_id, planned_runtime_minutes, actual_runtime_minutes, downtime_minutes, production_count, rejection_count, target_count |
| `downtime_logs`    | date, machine_id, reason, downtime_minutes                                  |
| `machine_alerts`   | timestamp, machine_id, alert_type, severity                                 |

- **Date range:** 2026-04-01 → 2026-05-30  
- **Machines:** M001 – M010  
- **Records:** 600 production logs, 150 downtime logs, 100 alerts

---

## 🔧 Backend Functions (Tools)

| Function | Purpose | Parameters |
|---|---|---|
| `calculate_oee` | OEE for a specific machine | machine_id, start_date, end_date |
| `get_downtime_analytics` | Plant-wide downtime by machine | start_date, end_date |
| `get_machine_downtime` | Detailed downtime for one machine | machine_id, start_date, end_date |
| `get_rejection_analytics` | Plant-wide rejection by machine | start_date, end_date |
| `get_machine_rejection` | Detailed rejection for one machine | machine_id, start_date, end_date |
| `compare_machine_analytics` | Side-by-side comparison of two machines | machine1, machine2, start_date, end_date |
| `get_production_summary` | Plant-wide production overview | start_date, end_date |
| `get_machine_production_summary` | Daily production detail for one machine | machine_id, start_date, end_date |
| `get_maintenance_recommendation` | Recommendations based on alerts + downtime | start_date, end_date |

### OEE Formula
```
Availability = actual_runtime / planned_runtime
Performance  = production_count / target_count
Quality      = good_count / production_count
OEE          = Availability × Performance × Quality
```

---

## 🤖 AI Architecture

```
User Query
    ↓
Intent Classification  (local regex — no LLM cost)
    ↓
Conversational? → Canned reply (hi, bye, what can you do…)
Incomplete?     → Ask what to analyse
Gibberish?      → Suggest example queries
Manufacturing?  → ↓
    ↓
Parameter Extraction (LLM: qwen2.5:3b)
    ↓
Context Memory  (fill gaps from chat history)
    ↓
Missing Params? → Ask user (machine ID / date range)
    ↓
Execute Tool    (backend function, never raw SQL from AI)
    ↓
LLM Summary     (plain-English 2–3 sentence insight)
    ↓
Recommendations + Charts + Exports
```

---

## 🚀 Setup & Run

### Prerequisites
- Python 3.10+
- [Ollama](https://ollama.com) installed and running

### 1. Install Ollama model
```bash
ollama pull qwen2.5:3b
```

### 2. Install Python dependencies
```bash
pip install -r requirements.txt
```

### 3. Run the app
```bash
# From the project root directory
streamlit run dashboard/app.py
```

> ⚠️ Always run from the **project root**, not from inside `dashboard/`.

---

## 💬 Example Queries

| Query | What happens |
|---|---|
| `Hi` | Conversational reply |
| `OEE for M001` | Asks for date range |
| `OEE for M001 complete range` | Runs immediately using full DB range |
| `OEE for M001 2026-04-01 to 2026-04-30` | Runs directly |
| `Compare M001 and M002` | Asks for date range |
| `Compare with M002` | Uses M001 from context, asks for date |
| `Plant downtime complete range` | Runs plant-wide downtime |
| `Downtime for M003` | Runs machine-specific downtime |
| `asdfgh` | Gibberish → suggest examples |
| `Show` | Incomplete → list available analyses |

---

## 📊 Charts

| Analysis | Chart Type |
|---|---|
| OEE | Bar chart (Availability / Performance / Quality / OEE) with world-class 85% line |
| Plant Downtime | Pie chart + Horizontal bar |
| Machine Downtime | Horizontal bar by reason |
| Rejection | Bar chart coloured by rejection rate |
| Machine Rejection | Stacked bar (Good vs Rejection daily) |
| Machine Comparison | Grouped bar + OEE Radar |
| Production Summary | Bar (by machine) + Horizontal bar (utilisation) |
| Machine Production | Multi-line chart (production, target, rejection) |
| Maintenance | Table with issue and recommendation |

---

## 📥 Exports

Every analysis provides:
- **CSV download** — raw data table
- **PDF download** — formatted report with summary, data table, and recommendations (requires `reportlab`)

---

## 🗂️ Sidebar Features

- **System Status** — 🟢/🔴 for Database, Ollama, AI Ready
- **Session Info** — current machine, date range, last analysis
- **Recent Analyses** — last 5 analyses run
- **Quick Queries** — one-click common queries
- **Database Range** — shows min/max dates available
- **Clear Chat** — reset session

---

## 🛡️ Error Handling

The UI never shows raw Python errors. All exceptions are caught and displayed as friendly messages:
- `⚠️ No data found for machine X`
- `⚠️ Invalid parameters`
- `⚠️ Analysis failed. Please try again.`

---

## 📦 Dependencies

| Package | Purpose |
|---|---|
| `streamlit` | Web UI |
| `plotly` | Interactive charts |
| `pandas` | Data manipulation |
| `ollama` | LLM inference (local) |
| `requests` | Ollama health check |
| `reportlab` | PDF export |

---

## 🔑 Key Design Decisions

1. **AI never touches the DB** — the LLM only selects a function and extracts parameters; all DB access happens in `analytics_engine.py`.
2. **Intent classification is local** — conversational/gibberish/incomplete queries are handled with regex, saving LLM latency for real manufacturing queries.
3. **Context memory** — machine IDs and date ranges from earlier in the conversation are re-used automatically.
4. **Generic parameter collection** — one unified framework handles missing parameters for all 9 functions; no per-function special cases in the UI.
5. **Graceful degradation** — if Ollama is unavailable, the app still loads and shows appropriate status indicators.
