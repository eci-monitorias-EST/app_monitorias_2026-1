import streamlit as st

from pages.home import render as render_home
from pages.analytics import render as render_analytics


def build_navigation():
    home_page = st.Page(
        render_home,
        title="Inicio",
        icon="🏠",
        url_path="inicio",
        default=True,
    )

    analytics_page = st.Page(
        render_analytics,
        title="Analítica",
        icon="📈",
        url_path="analitica",
    )

    return st.navigation([home_page, analytics_page])