from datetime import datetime

import requests
import streamlit as st

from config.settings import (
    DEFAULT_TIMEOUT_SECONDS,
    get_form_token,
    get_script_url,
)


@st.dialog("Autorización de tratamiento de datos")
def _consent_dialog() -> None:
    st.write(
        "Esta recolección se realiza solo con fines académicos. "
        "De acuerdo con la Ley 1581 de 2012 (Colombia), art. 9 y art. 12, "
        "el tratamiento de datos personales requiere autorización previa e informada del titular."
    )
    accepted = st.checkbox(
        "He leído la información y autorizo el tratamiento de mis datos para fines académicos.",
        key="consent_checkbox",
    )

    reject_col, accept_col = st.columns(2)
    with reject_col:
        if st.button("No autorizo", use_container_width=True):
            st.session_state["data_consent"] = False
            st.rerun()

    with accept_col:
        if st.button(
            "Autorizo",
            type="primary",
            use_container_width=True,
            disabled=not accepted,
        ):
            st.session_state["data_consent"] = True
            st.rerun()


def _ensure_consent() -> bool:
    if "data_consent" not in st.session_state:
        st.session_state["data_consent"] = None

    if st.session_state["data_consent"] is True:
        return True

    _consent_dialog()
    if st.session_state["data_consent"] is False:
        st.error("No autorizaste el tratamiento de datos. No es posible continuar.")
        if st.button("Volver a mostrar autorización"):
            st.session_state["data_consent"] = None
            st.rerun()
    else:
        st.info("Debes autorizar el tratamiento de datos para habilitar el formulario.")

    return False


def _save_profile_in_session(payload: dict, backend_id: int | None = None) -> None:
    if backend_id is None or backend_id <= 0:
        raise ValueError("El backend no devolvió un id válido.")

    existing_profile = st.session_state.get("participant_profile")
    if existing_profile and existing_profile.get("id") not in (None, backend_id):
        raise ValueError("El id de sesión no puede cambiar durante la misma sesión.")

    st.session_state["participant_profile"] = {
        "id": backend_id,
        "Dia": payload["Dia"],
        "nombre": payload["nombre"],
        "sexo": payload["sexo"],
        "colegio": payload["colegio"],
    }


def render() -> None:
    st.title("Recolección de datos")
    st.write("Completa el formulario para registrar respuestas en Google Sheets.")

    existing_profile = st.session_state.get("participant_profile")
    if existing_profile and isinstance(existing_profile.get("id"), int) and existing_profile["id"] > 0:
        st.success(f"Sesión activa con id participante: {existing_profile['id']}")
        st.caption(
            f"Participante: {existing_profile['nombre']} | "
            f"Sexo: {existing_profile['sexo']} | Colegio: {existing_profile['colegio']}"
        )
        if st.button("Registrar otra persona en esta sesión"):
            st.session_state.pop("participant_profile", None)
            st.rerun()
        return

    if not _ensure_consent():
        return

    with st.form("formulario_recoleccion"):
        nombre = st.text_input("Nombre")
        sexo = st.selectbox("Sexo", ["", "Masculino", "Femenino", "Otro"])
        colegio = st.text_input("Colegio")

        submit = st.form_submit_button("Enviar")

    if not submit:
        return

    if not all([nombre, sexo, colegio]):
        st.warning("Completa todos los campos.")
        return

    payload = {
        "token": get_form_token(),
        "accion": "bienvenida",
        "Dia": datetime.now().strftime("%Y-%m-%d"),
        "nombre": nombre.strip(),
        "sexo": sexo,
        "colegio": colegio.strip(),
        "ejercicio": "bienvenida",
        "comentario": "",
    }

    try:
        response = requests.post(
            get_script_url(),
            json=payload,
            timeout=DEFAULT_TIMEOUT_SECONDS,
        )

        if response.status_code == 401:
            st.error(
                "El endpoint respondió 401 (Unauthorized). "
                "Revisa en Apps Script que la implementación web tenga acceso 'Anyone' o 'Anyone with link', "
                "y vuelve a implementar para generar una URL vigente."
            )
            return

        if not response.ok:
            st.error(
                f"Error HTTP {response.status_code} desde Apps Script. "
                "Verifica permisos del deployment y la URL publicada."
            )
            return

        try:
            resultado = response.json()
        except ValueError:
            st.error("El endpoint respondió con un formato no válido.")
            return

        if resultado.get("status") == "success":
            participant_id = resultado.get("id")
            normalized_id = None
            if isinstance(participant_id, int):
                normalized_id = participant_id
            elif isinstance(participant_id, str) and participant_id.isdigit():
                normalized_id = int(participant_id)

            _save_profile_in_session(payload, normalized_id)
            st.success("Registro guardado correctamente.")
            st.caption("Perfil del participante guardado en memoria de sesión para próximos comentarios.")
            st.caption(f"ID asignado: {normalized_id}")
        else:
            st.error(resultado.get("message", "Ocurrió un error."))
            if "expectedSheet" in resultado:
                st.caption(f"Hoja esperada por el backend: {resultado.get('expectedSheet')}")
            if "availableSheets" in resultado:
                st.caption(f"Hojas disponibles: {', '.join(resultado.get('availableSheets', []))}")
    except ValueError as exc:
        st.error(str(exc))
    except requests.RequestException as exc:
        st.error(f"Error de conexión: {exc}")
