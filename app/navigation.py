import streamlit as st

from pages.sequential_flow import render as render_sequential_flow


def build_navigation():
    flow_page = st.Page(
        render_sequential_flow,
        title="Flujo Secuencial",
        icon="🧭",
        url_path="flujo",
        default=True,
    )

    return st.navigation([flow_page])