import streamlit as st
from streamlit.errors import StreamlitSecretNotFoundError


DEFAULT_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbzCUZlvgznLte0Q1UmSRKJkePzCo7lu76FLz69bnc9vFhiTpcVlplSf_tZX9yxUuqfbjw/exec"
DEFAULT_FORM_TOKEN = "mi_token_123"
DEFAULT_TIMEOUT_SECONDS = 10


def _get_secret_or_default(key: str, default: str) -> str:
    try:
        return st.secrets[key]
    except (StreamlitSecretNotFoundError, KeyError):
        return default


def get_script_url() -> str:
    return _get_secret_or_default("google_script_url", DEFAULT_SCRIPT_URL)


def get_form_token() -> str:
    return _get_secret_or_default("google_script_token", DEFAULT_FORM_TOKEN)
