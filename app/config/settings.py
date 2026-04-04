from __future__ import annotations

import os

import streamlit as st
from streamlit.errors import StreamlitSecretNotFoundError


DEFAULT_SCRIPT_URL = ""
DEFAULT_FORM_TOKEN = ""
DEFAULT_TIMEOUT_SECONDS = int(os.getenv("APP_TIMEOUT_SECONDS", "10"))


def _get_secret_or_env(key: str, env_key: str, default: str) -> str:
    env_value = os.getenv(env_key)
    if env_value:
        return env_value
    try:
        return str(st.secrets[key])
    except (StreamlitSecretNotFoundError, KeyError):
        return default


def get_script_url() -> str:
    return _get_secret_or_env("google_script_url", "GOOGLE_SCRIPT_URL", DEFAULT_SCRIPT_URL)


def get_form_token() -> str:
    return _get_secret_or_env("google_script_token", "GOOGLE_SCRIPT_TOKEN", DEFAULT_FORM_TOKEN)
