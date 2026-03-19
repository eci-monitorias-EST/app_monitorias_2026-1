import streamlit as st

from pages.home import render as render_home
from pages.analytics import render as render_analytics
from pages.data_collection import render as render_data_collection
from pages.exercise_1 import render as render_exercise_1


def build_navigation():
    data_collection_page = st.Page(
        render_data_collection,
        title="Recolección",
        icon="📝",
        url_path="recoleccion",
        default=True,
    )

    home_page = st.Page(
        render_home,
        title="Inicio",
        icon="🏠",
        url_path="inicio",
    )

    analytics_page = st.Page(
        render_analytics,
        title="Analítica",
        icon="📈",
        url_path="analitica",
    )

    exercise_1_page = st.Page(
        render_exercise_1,
        title="Ejercicio 1",
        icon="✍️",
        url_path="ejercicio-1",
    )

    return st.navigation([home_page, analytics_page, data_collection_page, exercise_1_page])