from __future__ import annotations

import streamlit as st


def inject_global_styles() -> None:
    st.markdown(
        """
        <style>
        .stApp {
            background:
                radial-gradient(circle at top left, rgba(56, 189, 248, 0.15), transparent 30%),
                radial-gradient(circle at top right, rgba(21, 94, 239, 0.12), transparent 26%),
                linear-gradient(180deg, #f8fbff 0%, #eef4ff 100%);
        }
        .bankify-hero {
            background: linear-gradient(120deg, #0f172a 0%, #155eef 58%, #38bdf8 100%);
            color: #ffffff;
            padding: 2.4rem;
            border-radius: 24px;
            box-shadow: 0 20px 55px rgba(15, 23, 42, 0.18);
            margin-bottom: 1.1rem;
        }
        .bankify-card {
            background: rgba(255, 255, 255, 0.88);
            border: 1px solid rgba(21, 94, 239, 0.12);
            border-radius: 20px;
            padding: 1.1rem 1.2rem;
            box-shadow: 0 12px 30px rgba(15, 23, 42, 0.08);
            min-height: 150px;
        }
        .bankify-pill {
            display: inline-block;
            background: rgba(21, 94, 239, 0.1);
            color: #0f172a;
            border-radius: 999px;
            padding: 0.25rem 0.75rem;
            margin-right: 0.45rem;
            margin-bottom: 0.45rem;
            font-size: 0.82rem;
            font-weight: 600;
        }
        .step-chip {
            display: inline-block;
            padding: 0.38rem 0.8rem;
            border-radius: 999px;
            margin: 0 0.35rem 0.45rem 0;
            background: rgba(15, 23, 42, 0.06);
            color: #0f172a;
            font-size: 0.82rem;
        }
        .step-chip.active {
            background: #155eef;
            color: #ffffff;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
