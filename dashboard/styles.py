def load_css():
    return """
    <style>

    .stApp {
        background-color: #0f1117;
        color: #e0e0e0;
    }

    .stChatInput input {
        background-color: #1e2130 !important;
        border: 1px solid #3a3f5c !important;
        color: #e0e0e0 !important;
        border-radius: 12px !important;
    }

    section[data-testid="stSidebar"] {
        background-color: #13151f;
        border-right: 1px solid #2a2d3e;
    }

    div[data-testid="metric-container"] {
        background: linear-gradient(
            135deg,
            #1e2130,
            #252840
        );

        border: 1px solid #3a3f5c;
        border-radius: 12px;
        padding: 16px;
    }

    .stButton > button {
        background: linear-gradient(
            135deg,
            #3a7bd5,
            #2563b0
        );

        color: white;
        border: none;
        border-radius: 8px;
        padding: 8px 16px;
        font-weight: 600;
        transition: 0.2s;
    }

    .stButton > button:hover {
        transform: translateY(-1px);
        background: linear-gradient(
            135deg,
            #4a8be5,
            #3573c0
        );
    }

    .kpi-card {
        background: linear-gradient(
            135deg,
            #1e2130,
            #252840
        );

        border: 1px solid #3a3f5c;
        border-radius: 12px;
        padding: 20px;
        text-align: center;
    }

    .kpi-value {
        font-size: 28px;
        font-weight: 700;
        color: #60a5fa;
    }

    .kpi-label {
        font-size: 13px;
        color: #8899aa;
        margin-top: 5px;
    }

    .analysis-card {
        background: #1e2130;
        border: 1px solid #3a3f5c;
        border-radius: 12px;
        padding: 18px;
        margin-bottom: 15px;
    }

    .analysis-card h4 {
        color: #60a5fa;
        margin-bottom: 10px;
    }

    .analysis-card p {
        color: #cbd5e1;
        margin: 4px 0;
        font-size: 14px;
    }

    .rec-pill {
        display: inline-block;
        background: #1a2a1a;
        border: 1px solid #2a4a2a;
        border-radius: 20px;
        padding: 6px 14px;
        margin: 4px;
        color: #6abf6a;
        font-size: 13px;
    }

    .status-ok {
        color: #4ade80;
        font-weight: 600;
    }

    .status-err {
        color: #f87171;
        font-weight: 600;
    }

    .welcome-box {
        background: linear-gradient(
            135deg,
            #1a2040,
            #1e2840
        );

        border: 1px solid #3a4a6c;
        border-radius: 16px;
        padding: 32px;
        text-align: center;
        margin: 40px auto;
        max-width: 700px;
    }

    .welcome-box h2 {
        color: #60a5fa;
        font-size: 28px;
        margin-bottom: 10px;
    }

    .welcome-box p {
        color: #cbd5e1;
        font-size: 15px;
    }

    .param-box {
        background: #161928;
        border: 1px solid #3a4a6c;
        border-radius: 12px;
        padding: 20px;
        margin-top: 10px;
        margin-bottom: 10px;
    }

    .footer-card {
        background: #161928;
        border: 1px solid #2a2d3e;
        border-radius: 12px;
        padding: 12px;
        margin-top: 15px;
    }

    .stExpander {
        border-radius: 12px;
    }

    .stDataFrame {
        border-radius: 10px;
    }

    hr {
        border-color: #2a2d3e;
    }

    </style>
    """