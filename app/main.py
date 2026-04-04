import streamlit as st

from navigation import build_navigation

st.set_page_config(
    page_title="Monitorias",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

navigation = build_navigation()
navigation.run()