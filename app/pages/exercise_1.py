import requests
import streamlit as st

from config.settings import (
    DEFAULT_TIMEOUT_SECONDS,
    get_form_token,
    get_script_url,
)


def _get_session_profile() -> dict | None:
    profile = st.session_state.get("participant_profile")
    if not profile:
        return None

    participant_id = profile.get("id")
    if not isinstance(participant_id, int) or participant_id <= 0:
        return None

    return profile


def render() -> None:
    st.title("Ejercicio 1")
    st.write("Envía un comentario para el participante activo en sesión.")

    profile = _get_session_profile()
    if profile is None:
        st.warning("Primero debes completar Recolección para crear un id de participante válido.")
        return

    st.info(
        f"Participante ID: {profile['id']} | "
        f"Nombre: {profile.get('nombre', '')} | "
        f"Colegio: {profile.get('colegio', '')}"
    )

    with st.form("formulario_ejercicio_1"):
        comentario = st.text_area("Comentario", placeholder="Escribe aquí el comentario del ejercicio 1")
        submit = st.form_submit_button("Guardar ejercicio 1")

    if not submit:
        return

    comentario = comentario.strip()
    if not comentario:
        st.warning("El comentario es obligatorio.")
        return

    payload = {
        "token": get_form_token(),
        "accion": "ejercicio",
        "id": profile["id"],
        "ejercicio": "ejercicio_1",
        "comentario": comentario,
    }

    try:
        response = requests.post(
            get_script_url(),
            json=payload,
            timeout=DEFAULT_TIMEOUT_SECONDS,
        )

        if not response.ok:
            st.error(f"Error HTTP {response.status_code} desde Apps Script.")
            return

        try:
            resultado = response.json()
        except ValueError:
            st.error("El endpoint respondió con un formato no válido.")
            return

        if resultado.get("status") == "success":
            st.success(f"Ejercicio 1 guardado con id participante {profile['id']}.")
        else:
            st.error(resultado.get("message", "Ocurrió un error al guardar ejercicio 1."))
    except requests.RequestException as exc:
        st.error(f"Error de conexión: {exc}")
