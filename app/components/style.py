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
            position: relative;
            overflow: hidden;
            background: linear-gradient(120deg, #08245c 0%, #1267cf 58%, #3a7cf0 100%);
            color: #ffffff;
            padding: 2.25rem 2.55rem;
            border-radius: 18px;
            box-shadow: 0 22px 55px rgba(15, 23, 42, 0.18);
            margin: 0 auto 1.35rem;
            max-width: 1080px;
        }
        .bankify-hero::after {
            content: "";
            position: absolute;
            width: 360px;
            height: 360px;
            right: 8%;
            top: -82px;
            border-radius: 50%;
            background: rgba(255, 255, 255, 0.14);
        }
        .bankify-hero h1,
        .bankify-hero p,
        .bankify-hero div {
            position: relative;
            z-index: 1;
        }
        .bankify-hero h1 {
            margin: 0 0 1rem;
            font-size: 2.55rem;
            line-height: 1.05;
            letter-spacing: 0;
        }
        .bankify-hero p {
            max-width: 760px;
            color: rgba(255, 255, 255, 0.82);
            font-size: 1rem;
            line-height: 1.65;
            margin-bottom: 1.5rem;
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
            background: rgba(255, 255, 255, 0.12);
            color: #ffffff;
            border: 1px solid rgba(255, 255, 255, 0.28);
            border-radius: 999px;
            padding: 0.35rem 0.85rem;
            margin-right: 0.45rem;
            margin-bottom: 0.45rem;
            font-size: 0.76rem;
            font-weight: 600;
        }
        .bankify-access-heading {
            background: rgba(255, 255, 255, 0.96);
            border: 1px solid rgba(148, 163, 184, 0.16);
            border-bottom: 0;
            border-radius: 18px 18px 0 0;
            box-shadow: 0 24px 70px rgba(15, 23, 42, 0.12);
            margin-top: 0.25rem;
            padding: 2.2rem 2.4rem 0.65rem;
            text-align: center;
        }
        .bankify-access-heading h2 {
            color: #08245c;
            font-size: 1.35rem;
            margin: 0 0 0.55rem;
            letter-spacing: 0;
        }
        .bankify-access-heading p {
            color: #4b5563;
            margin: 0;
        }
        div[data-testid="stForm"]:has(input[aria-label="Nombre"]) {
            background: rgba(255, 255, 255, 0.96);
            border: 1px solid rgba(148, 163, 184, 0.16);
            border-top: 0;
            border-radius: 0 0 18px 18px;
            box-shadow: 0 24px 70px rgba(15, 23, 42, 0.12);
            padding: 0.75rem 2.4rem 2.2rem;
        }
        div[data-testid="stForm"]:has(input[aria-label="Nombre"]) label {
            color: #6b7280;
            font-size: 0.68rem;
            font-weight: 700;
            letter-spacing: 0.08em;
            text-transform: uppercase;
        }
        div[data-testid="stForm"]:has(input[aria-label="Nombre"]) input {
            min-height: 3.25rem;
            border-radius: 10px;
            background: #f8fafc;
            border-color: #cbd5e1;
            color: #111827;
        }
        div[data-testid="stForm"]:has(input[aria-label="Nombre"]) button {
            min-height: 3.15rem;
            border-radius: 10px;
            font-weight: 700;
        }
        div[data-testid="stForm"] {
            background: #ffffff;
            border: 1px solid rgba(148, 163, 184, 0.16);
            border-radius: 18px;
            box-shadow: 0 16px 40px rgba(15, 23, 42, 0.08);
            padding: 1.25rem 1.4rem 1.35rem;
            margin-top: 1.35rem;
        }
        div[data-testid="stForm"] textarea,
        div[data-testid="stForm"] input {
            border-radius: 12px !important;
            border-color: #cbd5e1 !important;
            background: #f8fafc !important;
        }
        div[data-testid="stForm"] button {
            border-radius: 12px !important;
            min-height: 3.1rem;
            font-weight: 800;
        }
        .bankify-prediction-hero {
            display: grid;
            grid-template-columns: minmax(0, 1.45fr) minmax(260px, 1fr);
            gap: 1.5rem;
            background: linear-gradient(135deg, #08245c 0%, #1367cf 100%);
            border-radius: 24px;
            color: #ffffff;
            padding: 2rem;
            margin: 1.5rem 0;
        }
        .bankify-prediction-hero h1 {
            margin: 0.2rem 0 0.8rem;
            font-size: 2rem;
            letter-spacing: -0.03em;
        }
        .bankify-prediction-hero p {
            color: rgba(226, 236, 255, 0.84);
            line-height: 1.65;
            max-width: 680px;
        }
        .bankify-prediction-summary {
            background: rgba(255, 255, 255, 0.12);
            border: 1px solid rgba(255, 255, 255, 0.18);
            border-radius: 18px;
            padding: 1.35rem 1.45rem;
            min-height: 240px;
        }
        .bankify-prediction-summary h2 {
            color: #e2eefa;
            margin: 0 0 0.55rem;
        }
        .bankify-prediction-summary .bankify-metric-label {
            color: #c7d8ff;
            font-size: 0.92rem;
            margin-bottom: 0.8rem;
            display: block;
        }
        .bankify-prediction-summary .bankify-metric-value {
            color: #ffffff;
            font-size: 2.4rem;
            font-weight: 800;
            margin: 0;
        }
        .bankify-prediction-summary .bankify-metric-subtitle {
            color: rgba(226, 236, 255, 0.78);
            margin-top: 0.2rem;
        }
        .bankify-prediction-summary .bankify-prediction-tag {
            display: inline-block;
            margin-top: 1rem;
            padding: 0.35rem 0.75rem;
            border-radius: 999px;
            background: rgba(255, 255, 255, 0.16);
            color: #dbeafe;
            font-size: 0.75rem;
            font-weight: 700;
            letter-spacing: 0.05em;
            text-transform: uppercase;
        }
        .bankify-prediction-panel {
            display: grid;
            grid-template-columns: 1.3fr 1fr;
            gap: 1rem;
            margin-bottom: 1.5rem;
        }
        .bankify-prediction-panel-left,
        .bankify-prediction-panel-right {
            background: rgba(255, 255, 255, 0.94);
            border: 1px solid rgba(14, 90, 207, 0.12);
            border-radius: 20px;
            padding: 1.35rem 1.4rem;
            box-shadow: 0 18px 30px rgba(15, 23, 42, 0.06);
        }
        .bankify-prediction-panel-left h2,
        .bankify-prediction-panel-right h2 {
            margin-top: 0;
            margin-bottom: 0.75rem;
            color: #08245c;
        }
        .bankify-prediction-panel-left p,
        .bankify-prediction-panel-right p {
            margin: 0;
            color: #475569;
            line-height: 1.7;
        }
        .bankify-prediction-panel-right {
            display: flex;
            flex-direction: column;
            justify-content: center;
        }
        .bankify-prediction-output {
            background: #ffffff;
            border: 1px solid rgba(14, 90, 207, 0.14);
            border-radius: 24px;
            box-shadow: 0 24px 48px rgba(15, 23, 42, 0.08);
            padding: 1.5rem;
            margin-bottom: 1rem;
        }
        .bankify-prediction-output h2 {
            margin: 0 0 0.75rem;
            color: #08245c;
        }
        .bankify-prediction-output .bankify-metric-label {
            color: #475569;
            font-size: 0.85rem;
            display: block;
            margin-bottom: 0.5rem;
        }
        .bankify-prediction-output .bankify-metric-value {
            color: #0f172a;
            font-size: 2.35rem;
            margin: 0;
        }
        .bankify-prediction-output .bankify-metric-subtitle {
            color: #64748b;
            margin: 0.65rem 0 0;
            line-height: 1.65;
        }
        .bankify-prediction-badge {
            display: inline-flex;
            margin-top: 1rem;
            padding: 0.4rem 0.85rem;
            border-radius: 999px;
            background: #eff6ff;
            color: #1d4ed8;
            font-size: 0.75rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }
        .bankify-dictionary-row:first-child .bankify-dictionary-cell {
            border-top: none;
        }
        .bankify-result-card {
            background: #f8fbff;
            border: 1px solid rgba(15, 23, 42, 0.08);
            border-radius: 18px;
            padding: 1.3rem 1.45rem;
            margin-bottom: 1rem;
        }
        .bankify-result-card h3 {
            margin: 0 0 0.75rem;
            color: #08245c;
            font-size: 1.15rem;
        }
        .bankify-result-card p {
            margin: 0.35rem 0;
            color: #334155;
        }
        .bankify-form-footer {
            border-top: 1px solid rgba(148, 163, 184, 0.18);
            margin-top: 1rem;
            padding-top: 1rem;
        }
        .bankify-form-footer p {
            color: #475569;
            margin: 0;
            font-size: 0.92rem;
        }
        .bankify-profile-hero {
            position: relative;
            overflow: hidden;
            background: linear-gradient(90deg, #061b52 0%, #082760 52%, #0b3a81 100%);
            border-radius: 8px;
            color: #ffffff;
            margin: 0.35rem 0 1.5rem;
            padding: 1.55rem 1.7rem;
            min-height: 150px;
        }
        .bankify-profile-hero::after {
            content: "";
            position: absolute;
            inset: 0 0 0 auto;
            width: 46%;
            background:
                linear-gradient(90deg, rgba(6, 27, 82, 0.2), rgba(7, 38, 96, 0.88)),
                repeating-linear-gradient(90deg, transparent 0 14px, rgba(96, 165, 250, 0.18) 14px 15px);
            opacity: 0.72;
        }
        .bankify-profile-hero > div {
            position: relative;
            z-index: 1;
            max-width: 680px;
        }
        .bankify-profile-kicker {
            font-weight: 700;
            margin: 0 0 0.75rem;
        }
        .bankify-code-pill {
            display: inline-block;
            background: rgba(255, 255, 255, 0.18);
            border: 1px solid rgba(255, 255, 255, 0.22);
            border-radius: 999px;
            font-weight: 800;
            padding: 0.42rem 0.78rem;
        }
        .bankify-profile-copy {
            color: rgba(191, 219, 254, 0.92);
            line-height: 1.5;
            margin: 1rem 0 0;
        }
        .bankify-history-link {
            color: #0057c8;
            font-weight: 700;
            margin: 0;
            text-align: right;
        }
        .bankify-process-card {
            background: #ffffff;
            border: 1px solid rgba(15, 23, 42, 0.1);
            border-radius: 8px;
            box-shadow: 0 10px 24px rgba(15, 23, 42, 0.06);
            min-height: 182px;
            padding: 1.3rem 1.35rem;
            margin-bottom: 0.75rem;
        }
        .bankify-process-top,
        .bankify-progress-row {
            align-items: center;
            display: flex;
            justify-content: space-between;
            gap: 1rem;
        }
        .bankify-process-icon {
            align-items: center;
            background: #eaf4ff;
            border-radius: 8px;
            color: #006bd6;
            display: inline-flex;
            font-size: 1.25rem;
            font-weight: 800;
            height: 2.35rem;
            justify-content: center;
            width: 2.35rem;
        }
        .bankify-process-status {
            border-radius: 999px;
            font-size: 0.78rem;
            font-weight: 800;
            padding: 0.28rem 0.65rem;
        }
        .bankify-process-status.progress {
            background: #eaf4ff;
            color: #006bd6;
        }
        .bankify-process-status.new {
            background: #eef0f3;
            color: #6b7280;
        }
        .bankify-process-card h3 {
            color: #334155;
            font-size: 0.98rem;
            letter-spacing: 0;
            margin: 1.45rem 0 1.1rem;
        }
        .bankify-progress-row {
            color: #6b7280;
            font-size: 0.88rem;
            font-weight: 800;
            margin-bottom: 0.55rem;
        }
        .bankify-progress-row strong {
            color: #374151;
        }
        .bankify-progress-track {
            background: #edf0f4;
            border-radius: 999px;
            height: 0.45rem;
            overflow: hidden;
        }
        .bankify-progress-track span {
            background: #006bd6;
            border-radius: inherit;
            display: block;
            height: 100%;
            min-width: 0.35rem;
        }
        .bankify-data-hero {
            align-items: center;
            background: linear-gradient(90deg, #12377f 0%, #17377d 72%, #102f73 100%);
            border-radius: 8px;
            box-shadow: 0 14px 28px rgba(15, 23, 42, 0.16);
            color: #ffffff;
            display: flex;
            justify-content: space-between;
            margin: 0.5rem auto 1.6rem;
            max-width: 1180px;
            min-height: 190px;
            padding: 2rem 2.4rem;
        }
        .bankify-data-hero h1 {
            color: #c7dcff;
            font-size: 1.55rem;
            letter-spacing: 0;
            margin: 0 0 0.75rem;
        }
        .bankify-data-hero p {
            color: rgba(219, 234, 254, 0.68);
            line-height: 1.45;
            margin: 0.85rem 0 0;
            max-width: 760px;
        }
        .bankify-filter-pill {
            background: rgba(0, 107, 214, 0.35);
            border-radius: 4px;
            color: #60a5fa;
            display: inline-block;
            font-size: 0.7rem;
            font-weight: 800;
            letter-spacing: 0.04em;
            padding: 0.3rem 0.65rem;
            text-transform: uppercase;
        }
        .bankify-dictionary-table-wrapper {
            width: 100%;
            overflow-x: auto;
            margin-top: 1.2rem;
        }
        .bankify-dictionary-table {
            width: 100%;
            border-collapse: collapse;
            min-width: 720px;
        }
        .bankify-dictionary-head-row {
            background: #f8fafc;
        }
        .bankify-dictionary-head {
            color: #4b5563;
            font-size: 0.72rem;
            font-weight: 900;
            letter-spacing: 0.08em;
            padding: 1rem 1.2rem;
            text-align: left;
            text-transform: uppercase;
            border-bottom: 1px solid #dbe5ff;
        }
        .bankify-dictionary-row + .bankify-dictionary-row td {
            border-top: 1px solid #edf0f4;
        }
        .bankify-dictionary-cell {
            color: #4b5563;
            padding: 1rem 1.2rem;
            vertical-align: top;
        }
        .bankify-dictionary-cell.bankify-var-name {
            color: #001a4d !important;
            font-weight: 800;
        }
        .bankify-book-icon {
            color: rgba(0, 107, 214, 0.7);
            font-size: 4rem;
            font-weight: 800;
        }
        .bankify-dictionary-card {
            background: #ffffff;
            border: 1px solid rgba(15, 23, 42, 0.08);
            border-radius: 8px;
            box-shadow: 0 8px 18px rgba(15, 23, 42, 0.08);
            margin: 0 auto 1.6rem;
            max-width: 1180px;
            overflow: hidden;
        }
        .bankify-dictionary-card header {
            align-items: center;
            background: #e5e7eb;
            display: flex;
            gap: 0.85rem;
            padding: 1.2rem 1.45rem;
        }
        .bankify-dictionary-card h2 {
            color: #001a4d;
            font-size: 1.35rem;
            letter-spacing: 0;
            margin: 0;
        }
        .bankify-section-icon {
            color: #006bd6;
            font-size: 1.2rem;
        }
        .bankify-dictionary-table-wrapper {
            width: 100%;
            overflow-x: auto;
            margin-top: 1.2rem;
        }
        .bankify-dictionary-table {
            width: 100%;
            border-collapse: collapse;
            min-width: 720px;
        }
        .bankify-dictionary-head-row {
            background: #f8fafc;
        }
        .bankify-dictionary-head {
            color: #4b5563;
            font-size: 0.72rem;
            font-weight: 900;
            letter-spacing: 0.08em;
            padding: 1rem 1.2rem;
            text-align: left;
            text-transform: uppercase;
            border-bottom: 1px solid #dbe5ff;
        }
        .bankify-dictionary-row + .bankify-dictionary-row td {
            border-top: 1px solid #edf0f4;
        }
        .bankify-dictionary-cell {
            color: #4b5563;
            padding: 1rem 1.2rem;
            vertical-align: top;
        }
        .bankify-dictionary-cell.bankify-var-name {
            color: #001a4d !important;
            font-weight: 800;
        }
        .bankify-type-badge {
            background: #dbe5ff;
            border-radius: 4px;
            color: #1e3a8a;
            display: inline-block;
            font-size: 0.78rem;
            font-weight: 800;
            padding: 0.28rem 0.55rem;
        }
        .bankify-question-box {
            margin: 1.5rem 0 1rem;
            padding: 1.25rem 1.35rem;
            border-radius: 16px;
            background: #f8fbff;
            border: 1px solid #dbe5ff;
            box-shadow: 0 12px 24px rgba(15, 23, 42, 0.08);
        }
        .bankify-question-box-tag {
            display: inline-block;
            margin-bottom: 0.75rem;
            background: #0f2c6b;
            color: #ffffff;
            border-radius: 999px;
            padding: 0.26rem 0.72rem;
            font-size: 0.72rem;
            font-weight: 800;
            letter-spacing: 0.08em;
            text-transform: uppercase;
        }
        .bankify-question-box p {
            margin: 0;
            color: #334155;
            font-size: 1rem;
            line-height: 1.55;
        }
        .bankify-eda-gallery {
            background: rgba(255, 255, 255, 0.82);
            border: 1px solid rgba(15, 23, 42, 0.08);
            border-radius: 8px;
            padding: 1rem;
            margin-bottom: 1rem;
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
