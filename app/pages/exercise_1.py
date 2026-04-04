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


def _post_payload(payload: dict) -> dict | None:
    try:
        response = requests.post(
            get_script_url(),
            json=payload,
            timeout=DEFAULT_TIMEOUT_SECONDS,
        )

        if not response.ok:
            st.error(f"Error HTTP {response.status_code} desde Apps Script.")
            return None

        try:
            return response.json()
        except ValueError:
            st.error("El endpoint respondió con un formato no válido.")
            return None
    except requests.RequestException as exc:
        st.error(f"Error de conexión: {exc}")
        return None


def _sent_key(participant_id: int) -> str:
    return f"exercise_1_sent_{participant_id}"


def _notice_key(participant_id: int) -> str:
    return f"exercise_1_notice_seen_{participant_id}"


@st.dialog("Confirmación de modo de edición")
def _update_mode_dialog(notice_key: str) -> None:
    st.write(
        "Ya enviaste el comentario de Ejercicio 1 una vez. "
        "A partir de ahora, los envíos serán actualizaciones del mismo comentario "
        "(veces 2, 3, 4, ..., n), no nuevos registros."
    )
    if st.button("Entendido", type="primary"):
        st.session_state[notice_key] = True
        st.rerun()


def _show_action_error(message: str, *, context: str) -> None:
    normalized = message.lower()
    if context == "registrar" and "usa actualizar_ejercicio" in normalized:
        st.warning("Ya existe un comentario previo para este ejercicio. Usa la pestaña 'Actualizar comentario'.")
        return
    if context == "actualizar" and "no existe un registro" in normalized:
        st.warning("No hay comentario previo para actualizar. Primero registra el comentario en la pestaña 'Registrar comentario'.")
        return

    st.error(message)


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

    participant_id = profile["id"]
    sent_key = _sent_key(participant_id)
    notice_key = _notice_key(participant_id)

    comment_sent_once = bool(st.session_state.get(sent_key, False))
    if comment_sent_once and not bool(st.session_state.get(notice_key, False)):
        _update_mode_dialog(notice_key)

    if not comment_sent_once:
        st.caption("Primer envío: se registra el comentario. Después, solo se podrá actualizar.")
        with st.form("formulario_ejercicio_1_registrar"):
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
            "id": participant_id,
            "ejercicio": "ejercicio_1",
            "comentario": comentario,
        }
        resultado = _post_payload(payload)
        if resultado and resultado.get("status") == "success":
            st.session_state[sent_key] = True
            st.session_state[notice_key] = False
            st.success(f"Ejercicio 1 guardado con id participante {participant_id}.")
            st.rerun()
        elif resultado:
            message = resultado.get("message", "Ocurrió un error al guardar ejercicio 1.")
            if "usa actualizar_ejercicio" in message.lower():
                st.session_state[sent_key] = True
                st.session_state[notice_key] = False
                st.warning("Ya había un comentario previo. Se activó modo de actualización.")
                st.rerun()
            else:
                _show_action_error(message, context="registrar")
        return

    st.caption("Modo actualización: a partir del segundo envío, solo se actualiza el comentario existente.")
    with st.form("formulario_ejercicio_1_actualizar"):
        nuevo_comentario = st.text_area(
            "Nuevo comentario",
            placeholder="Escribe la versión actualizada del comentario",
        )
        submit_update = st.form_submit_button("Actualizar comentario")

    if not submit_update:
        return

    nuevo_comentario = nuevo_comentario.strip()
    if not nuevo_comentario:
        st.warning("El nuevo comentario es obligatorio.")
        return

    payload = {
        "token": get_form_token(),
        "accion": "actualizar_ejercicio",
        "id": participant_id,
        "ejercicio": "ejercicio_1",
        "comentario": nuevo_comentario,
    }
    resultado = _post_payload(payload)
    if resultado and resultado.get("status") == "success":
        st.success(f"Comentario actualizado para el id participante {participant_id}.")
    elif resultado:
        _show_action_error(
            resultado.get("message", "Ocurrió un error al actualizar comentario."),
            context="actualizar",
        )
