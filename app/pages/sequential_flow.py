from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Callable

import pandas as pd
import plotly.express as px
import requests
import streamlit as st

from config.settings import DEFAULT_TIMEOUT_SECONDS, get_form_token, get_script_url


@dataclass(frozen=True)
class StepDefinition:
    number: int
    title: str
    render_fn: str


class SequentialLearningFlow:
    STEPS = [
        StepDefinition(1, "Bienvenida y contexto", "_render_step_1"),
        StepDefinition(2, "Recolección de datos", "_render_step_2"),
        StepDefinition(3, "Visualización conjunto de datos (Ejercicio 1)", "_render_step_3"),
        StepDefinition(4, "Visualización con gráficas (Ejercicio 2)", "_render_step_4"),
        StepDefinition(5, "Predicción (Ejercicio 3)", "_render_step_5"),
        StepDefinition(6, "Gráfico tridimensional (Ejercicio 4)", "_render_step_6"),
        StepDefinition(7, "Retroalimentación final", "_render_step_7"),
    ]

    EXERCISE_BY_STEP = {
        3: "ejercicio_1",
        4: "ejercicio_2",
        5: "ejercicio_3",
        6: "ejercicio_4",
    }

    DATASET_PATH = "data/raw/Default_Clientes.csv"

    def __init__(self) -> None:
        self._init_state()

    def render(self) -> None:
        current_step = st.session_state["current_step"]
        step = self.STEPS[current_step - 1]

        if current_step != 2:
            st.session_state["show_update_profile_form"] = False

        self._render_sidebar()

        st.title(f"Página {step.number}: {step.title}")
        st.progress(current_step / len(self.STEPS), text=f"Paso {current_step} de {len(self.STEPS)}")

        render_method: Callable[[], None] = getattr(self, step.render_fn)
        render_method()

        self._render_navigation()

    def _init_state(self) -> None:
        st.session_state.setdefault("current_step", 1)
        st.session_state.setdefault("data_consent", None)
        st.session_state.setdefault("participant_profile", None)
        st.session_state.setdefault("exercise_comments_sent", {})
        st.session_state.setdefault("exercise_notice_seen", {})
        st.session_state.setdefault("show_update_profile_form", False)

    def _render_sidebar(self) -> None:
        with st.sidebar:
            st.markdown("## Navegación del Flujo")
            current_step = st.session_state["current_step"]
            st.caption(f"Paso actual: {current_step} de {len(self.STEPS)}")
            for step in self.STEPS:
                prefix = "➡️" if step.number == current_step else "•"
                st.write(f"{prefix} {step.number}. {step.title}")

    def _normalize_id(self, value: object) -> int | None:
        if isinstance(value, int) and value > 0:
            return value
        if isinstance(value, str) and value.isdigit():
            parsed = int(value)
            if parsed > 0:
                return parsed
        return None

    def _build_missing_fields_tooltip(self, fields_status: list[tuple[str, bool]], action_label: str) -> str:
        missing = [label for label, ok in fields_status if not ok]
        if not missing:
            return f"Todos los campos están completos. Ya puedes {action_label}."
        return f"Faltan campos obligatorios: {', '.join(missing)}"

    def _post_payload(self, payload: dict) -> dict | None:
        try:
            response = requests.post(
                get_script_url(),
                json=payload,
                timeout=DEFAULT_TIMEOUT_SECONDS,
            )
            if response.status_code == 401:
                st.error(
                    "El endpoint respondió 401 (Unauthorized). Verifica permisos del deployment en Apps Script."
                )
                return None

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

    @st.dialog("Autorización de tratamiento de datos")
    def _consent_dialog(self) -> None:
        st.write(
            "Esta recolección se realiza solo con fines académicos. "
            "De acuerdo con la Ley 1581 de 2012 (Colombia), art. 9 y art. 12, "
            "el tratamiento de datos personales requiere autorización previa e informada del titular."
        )
        accepted = st.checkbox(
            "He leído la información y autorizo el tratamiento de mis datos para fines académicos.",
            key="consent_checkbox",
        )
        no_col, yes_col = st.columns(2)
        with no_col:
            if st.button("No autorizo", use_container_width=True):
                st.session_state["data_consent"] = False
                st.rerun()
        with yes_col:
            if st.button("Autorizo", type="primary", use_container_width=True, disabled=not accepted):
                st.session_state["data_consent"] = True
                st.rerun()

    @st.dialog("Confirmación de modo de edición")
    def _update_mode_dialog(self, exercise_key: str) -> None:
        st.write(
            "Ya enviaste este comentario una vez. "
            "A partir de ahora, las veces 2, 3, 4, ..., n serán actualizaciones del mismo comentario."
        )
        if st.button("Entendido", type="primary"):
            notices = st.session_state["exercise_notice_seen"]
            notices[exercise_key] = True
            st.session_state["exercise_notice_seen"] = notices
            st.rerun()

    def _render_step_1(self) -> None:
        st.markdown(
            """
            Bienvenido al flujo de monitorías.

            En este recorrido completarás 4 ejercicios secuenciales:
            1. Visualización de conjunto de datos.
            2. Visualización con gráficas.
            3. Predicción.
            4. Gráfico tridimensional.

            Reglas del flujo:
            - No puedes avanzar al Ejercicio 1 sin completar recolección de datos.
            - En cada ejercicio debes enviar comentario para habilitar `Siguiente`.
            - Siempre puedes volver con `Atrás`.
            """
        )

    def _render_step_2(self) -> None:
        profile = st.session_state.get("participant_profile")

        if st.session_state["data_consent"] is not True:
            self._consent_dialog()
            if st.session_state["data_consent"] is False:
                st.error("No autorizaste el tratamiento de datos. No es posible continuar.")
            else:
                st.info("Autoriza el tratamiento de datos para continuar.")
            return

        if profile and self._normalize_id(profile.get("id")):
            participant_id = self._normalize_id(profile.get("id"))
            st.success(f"Sesión activa con id participante: {participant_id}")
            st.caption(
                f"Participante: {profile.get('nombre', '')} | Sexo: {profile.get('sexo', '')} | "
                f"Colegio: {profile.get('colegio', '')}"
            )

            if st.button("¿Quieres actualizar datos?", use_container_width=False):
                st.session_state["show_update_profile_form"] = True

            if st.session_state.get("show_update_profile_form", False):
                st.markdown("### Actualizar datos del participante")
                with st.form("actualizar_bienvenida_form"):
                    nombre = st.text_input("Nombre", value=str(profile.get("nombre", "")))
                    opciones = ["", "Masculino", "Femenino", "Otro"]
                    current_sex = str(profile.get("sexo", ""))
                    index = opciones.index(current_sex) if current_sex in opciones else 0
                    sexo = st.selectbox("Sexo", opciones, index=index)
                    colegio = st.text_input("Colegio", value=str(profile.get("colegio", "")))
                    edad = st.number_input(
                        "Edad",
                        min_value=5,
                        max_value=100,
                        value=int(profile.get("edad", 14)),
                        step=1,
                    )
                    grado_opciones = [
                        "Primero",
                        "Segundo",
                        "Tercero",
                        "Cuarto",
                        "Quinto",
                        "Sexto",
                        "Séptimo",
                        "Octavo",
                        "Noveno",
                        "Décimo",
                        "Undécimo",
                        "Bachiller",
                    ]
                    grado_actual = str(profile.get("grado", ""))
                    grado_index = grado_opciones.index(grado_actual) if grado_actual in grado_opciones else 0
                    grado = st.selectbox("Grado", grado_opciones, index=grado_index)
                    interes_carrera = st.text_area(
                        "¿Qué te llamó la atención de la carrera?",
                        value=str(profile.get("interes_carrera", "")),
                    )
                    matematicas_avanzadas = st.text_area(
                        "¿Qué fue lo más avanzado de matemáticas que has visto en el colegio?",
                        value=str(profile.get("matematicas_avanzadas", "")),
                    )

                    campos_llenos = all(
                        [
                            nombre.strip(),
                            sexo,
                            colegio.strip(),
                            str(edad).strip(),
                            grado,
                            interes_carrera.strip(),
                            matematicas_avanzadas.strip(),
                        ]
                    )
                    update_fields = [
                        ("Nombre", bool(nombre.strip())),
                        ("Sexo", bool(sexo)),
                        ("Colegio", bool(colegio.strip())),
                        ("Edad", bool(edad)),
                        ("Grado", bool(grado)),
                        ("Interés carrera", bool(interes_carrera.strip())),
                        ("Matemáticas avanzadas", bool(matematicas_avanzadas.strip())),
                    ]
                    update_help = self._build_missing_fields_tooltip(update_fields, "actualizar datos")
                    submit_update = st.form_submit_button(
                        "Actualizar datos",
                        help=update_help,
                    )

                if submit_update:
                    if not campos_llenos:
                        st.warning("Completa todos los campos para actualizar.")
                        return

                    payload = {
                        "token": get_form_token(),
                        "accion": "actualizar_bienvenida",
                        "id": participant_id,
                        "Dia": datetime.now().strftime("%Y-%m-%d"),
                        "nombre": nombre.strip(),
                        "sexo": sexo,
                        "colegio": colegio.strip(),
                        "edad": int(edad),
                        "grado": grado,
                        "interes_carrera": interes_carrera.strip(),
                        "matematicas_avanzadas": matematicas_avanzadas.strip(),
                    }
                    result = self._post_payload(payload)
                    if not result:
                        return
                    if result.get("status") == "success":
                        st.session_state["participant_profile"] = {
                            "id": participant_id,
                            "Dia": payload["Dia"],
                            "nombre": payload["nombre"],
                            "sexo": payload["sexo"],
                            "colegio": payload["colegio"],
                            "edad": payload["edad"],
                            "grado": payload["grado"],
                            "interes_carrera": payload["interes_carrera"],
                            "matematicas_avanzadas": payload["matematicas_avanzadas"],
                        }
                        st.session_state["show_update_profile_form"] = False
                        st.success("Datos actualizados correctamente.")
                    else:
                        st.error(result.get("message", "No fue posible actualizar datos."))
            return

        with st.form("registro_bienvenida_form"):
            nombre = st.text_input("Nombre")
            sexo = st.selectbox("Sexo", ["", "Masculino", "Femenino", "Otro"])
            colegio = st.text_input("Colegio")
            edad = st.number_input("Edad", min_value=5, max_value=100, value=14, step=1)
            grado = st.selectbox(
                "Grado",
                [
                    "",
                    "Primero",
                    "Segundo",
                    "Tercero",
                    "Cuarto",
                    "Quinto",
                    "Sexto",
                    "Séptimo",
                    "Octavo",
                    "Noveno",
                    "Décimo",
                    "Undécimo",
                    "Bachiller",
                ],
            )
            interes_carrera = st.text_area("¿Qué te llamó la atención de la carrera?")
            matematicas_avanzadas = st.text_area(
                "¿Qué fue lo más avanzado de matemáticas que has visto en el colegio?"
            )
            campos_llenos = all(
                [
                    nombre.strip(),
                    sexo,
                    colegio.strip(),
                    str(edad).strip(),
                    grado,
                    interes_carrera.strip(),
                    matematicas_avanzadas.strip(),
                ]
            )
            submit_fields = [
                ("Nombre", bool(nombre.strip())),
                ("Sexo", bool(sexo)),
                ("Colegio", bool(colegio.strip())),
                ("Edad", bool(edad)),
                ("Grado", bool(grado)),
                ("Interés carrera", bool(interes_carrera.strip())),
                ("Matemáticas avanzadas", bool(matematicas_avanzadas.strip())),
            ]
            submit_help = self._build_missing_fields_tooltip(submit_fields, "guardar datos")
            submit = st.form_submit_button("Guardar datos", help=submit_help)

        if not submit:
            return

        if not campos_llenos:
            st.warning("Completa todos los campos.")
            return

        payload = {
            "token": get_form_token(),
            "accion": "bienvenida",
            "Dia": datetime.now().strftime("%Y-%m-%d"),
            "nombre": nombre.strip(),
            "sexo": sexo,
            "colegio": colegio.strip(),
            "edad": int(edad),
            "grado": grado,
            "interes_carrera": interes_carrera.strip(),
            "matematicas_avanzadas": matematicas_avanzadas.strip(),
        }
        result = self._post_payload(payload)
        if not result:
            return

        if result.get("status") != "success":
            st.error(result.get("message", "No fue posible guardar los datos."))
            return

        participant_id = self._normalize_id(result.get("id"))
        if participant_id is None:
            st.error("El backend no devolvió un id válido.")
            return

        st.session_state["participant_profile"] = {
            "id": participant_id,
            "Dia": payload["Dia"],
            "nombre": payload["nombre"],
            "sexo": payload["sexo"],
            "colegio": payload["colegio"],
            "edad": payload["edad"],
            "grado": payload["grado"],
            "interes_carrera": payload["interes_carrera"],
            "matematicas_avanzadas": payload["matematicas_avanzadas"],
        }
        st.success(f"Registro guardado con id {participant_id}.")

    def _render_step_3(self) -> None:
        st.write("Explora una muestra del conjunto de datos.")
        df = self._load_dataset()
        st.dataframe(df.head(20), use_container_width=True)
        self._render_exercise_comment(step=3)

    def _render_step_4(self) -> None:
        st.write("Visualiza una gráfica para analizar el comportamiento de variables.")
        df = self._load_dataset()
        numeric_cols = df.select_dtypes(include="number").columns.tolist()
        if numeric_cols:
            col = numeric_cols[0]
            fig = px.histogram(df, x=col, nbins=30, title=f"Distribución de {col}")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No se encontraron columnas numéricas para graficar.")
        self._render_exercise_comment(step=4)

    def _render_step_5(self) -> None:
        st.write("Predicción simple de ejemplo para fines pedagógicos.")
        ingreso = st.slider("Ingreso mensual", min_value=0, max_value=20000000, value=2000000, step=100000)
        deuda = st.slider("Nivel de deuda", min_value=0.0, max_value=1.0, value=0.4, step=0.05)
        score = max(0.0, min(1.0, (deuda * 0.7) + (1 - min(ingreso / 10000000, 1)) * 0.3))
        st.metric("Riesgo estimado", f"{score * 100:.1f}%")
        self._render_exercise_comment(step=5)

    def _render_step_6(self) -> None:
        st.write("Gráfico tridimensional para explorar relaciones entre variables numéricas.")
        df = self._load_dataset()
        numeric_cols = df.select_dtypes(include="number").columns.tolist()

        if len(numeric_cols) >= 3:
            fig = px.scatter_3d(
                df.head(200),
                x=numeric_cols[0],
                y=numeric_cols[1],
                z=numeric_cols[2],
                title="Visualización 3D",
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No hay suficientes columnas numéricas para gráfico 3D.")

        self._render_exercise_comment(step=6)

    def _render_step_7(self) -> None:
        st.write("Comparte tu retroalimentación final del proceso.")
        self._render_feedback_form()

    def _load_dataset(self) -> pd.DataFrame:
        try:
            return pd.read_csv(self.DATASET_PATH)
        except Exception as exc:
            st.error(f"No fue posible cargar el dataset: {exc}")
            return pd.DataFrame()

    def _can_go_next(self, step: int) -> bool:
        if step == 1:
            return True
        if step == 2:
            profile = st.session_state.get("participant_profile")
            return bool(profile and self._normalize_id(profile.get("id")))
        if step in self.EXERCISE_BY_STEP:
            exercise_key = self.EXERCISE_BY_STEP[step]
            sent = st.session_state.get("exercise_comments_sent", {})
            return bool(sent.get(exercise_key, False))
        return False

    def _render_navigation(self) -> None:
        step = st.session_state["current_step"]
        back_col, next_col = st.columns(2)

        with back_col:
            if st.button("Atrás", use_container_width=True, disabled=step == 1):
                st.session_state["current_step"] = max(1, step - 1)
                st.rerun()

        with next_col:
            if step == len(self.STEPS):
                st.button("Siguiente", use_container_width=True, disabled=True)
                return

            can_next = self._can_go_next(step)
            if st.button("Siguiente", use_container_width=True, disabled=not can_next):
                st.session_state["current_step"] = min(len(self.STEPS), step + 1)
                st.rerun()

            if not can_next:
                if step == 2:
                    st.caption("Debes completar la recolección de datos para continuar.")
                elif step in self.EXERCISE_BY_STEP:
                    st.caption("Debes enviar el comentario de este ejercicio para continuar.")

    def _render_exercise_comment(self, step: int) -> None:
        profile = st.session_state.get("participant_profile")
        participant_id = self._normalize_id(profile.get("id") if profile else None)
        if participant_id is None:
            st.warning("Primero completa la recolección de datos para habilitar comentarios.")
            return

        exercise_key = self.EXERCISE_BY_STEP[step]
        sent_map = st.session_state.get("exercise_comments_sent", {})
        notice_map = st.session_state.get("exercise_notice_seen", {})
        already_sent = bool(sent_map.get(exercise_key, False))

        if already_sent and not bool(notice_map.get(exercise_key, False)):
            self._update_mode_dialog(exercise_key)

        title = "Actualizar comentario" if already_sent else "Registrar comentario"
        submit_label = "Actualizar comentario" if already_sent else "Enviar comentario"
        action = "actualizar_ejercicio" if already_sent else "ejercicio"

        with st.form(f"comment_form_{exercise_key}"):
            comentario = st.text_area("Comentario", placeholder=f"Escribe tu comentario para {exercise_key}")
            submit = st.form_submit_button(submit_label)

        if not submit:
            return

        comentario = comentario.strip()
        if not comentario:
            st.warning("El comentario es obligatorio.")
            return

        payload = {
            "token": get_form_token(),
            "accion": action,
            "id": participant_id,
            "ejercicio": exercise_key,
            "comentario": comentario,
        }

        result = self._post_payload(payload)
        if not result:
            return

        if result.get("status") == "success":
            sent_map[exercise_key] = True
            st.session_state["exercise_comments_sent"] = sent_map
            if already_sent:
                st.success("Comentario actualizado correctamente.")
            else:
                st.success("Comentario enviado correctamente.")
                notice_map[exercise_key] = False
                st.session_state["exercise_notice_seen"] = notice_map
            return

        message = result.get("message", "Ocurrió un error al procesar el comentario.")
        normalized = message.lower()

        if "usa actualizar_ejercicio" in normalized:
            sent_map[exercise_key] = True
            st.session_state["exercise_comments_sent"] = sent_map
            notice_map[exercise_key] = False
            st.session_state["exercise_notice_seen"] = notice_map
            st.warning("Ya existe un comentario previo. A partir de ahora solo puedes actualizarlo.")
            st.rerun()

        if "no existe un registro" in normalized:
            st.warning("No existe comentario previo para actualizar. Primero envía uno inicial.")
            sent_map[exercise_key] = False
            st.session_state["exercise_comments_sent"] = sent_map
            return

        st.error(message)

    def _render_feedback_form(self) -> None:
        profile = st.session_state.get("participant_profile")
        participant_id = self._normalize_id(profile.get("id") if profile else None)
        if participant_id is None:
            st.warning("Primero completa la recolección de datos para habilitar la retroalimentación.")
            return

        sent_key = f"retroalimentacion_sent_{participant_id}"
        notice_key = f"retroalimentacion_notice_seen_{participant_id}"
        already_sent = bool(st.session_state.get(sent_key, False))

        if already_sent and not bool(st.session_state.get(notice_key, False)):
            self._update_mode_dialog("retroalimentacion")

        submit_label = "Actualizar retroalimentación" if already_sent else "Enviar retroalimentación"
        action = "actualizar_retroalimentacion" if already_sent else "retroalimentacion"

        with st.form("retroalimentacion_form"):
            que_parecio = st.text_area("¿Qué te pareció el ejercicio?")
            que_hubiera_gustado = st.text_area("¿Qué te hubiera gustado hacer y/o ver?")
            cosas_mejorar = st.text_area("Cosas por mejorar")
            campos_llenos = all(
                [
                    que_parecio.strip(),
                    que_hubiera_gustado.strip(),
                    cosas_mejorar.strip(),
                ]
            )
            feedback_fields = [
                ("Qué te pareció", bool(que_parecio.strip())),
                ("Qué te hubiera gustado", bool(que_hubiera_gustado.strip())),
                ("Cosas por mejorar", bool(cosas_mejorar.strip())),
            ]
            feedback_help = self._build_missing_fields_tooltip(feedback_fields, submit_label.lower())
            submit = st.form_submit_button(submit_label, help=feedback_help)

        if not submit:
            return

        if not campos_llenos:
            st.warning("Completa todos los campos de retroalimentación.")
            return

        payload = {
            "token": get_form_token(),
            "accion": action,
            "id": participant_id,
            "que_parecio": que_parecio.strip(),
            "que_hubiera_gustado": que_hubiera_gustado.strip(),
            "cosas_mejorar": cosas_mejorar.strip(),
        }

        result = self._post_payload(payload)
        if not result:
            return

        if result.get("status") == "success":
            st.session_state[sent_key] = True
            if already_sent:
                st.success("Retroalimentación actualizada correctamente.")
            else:
                st.success("Retroalimentación enviada correctamente.")
                st.session_state[notice_key] = False
            return

        message = result.get("message", "Ocurrió un error al procesar la retroalimentación.")
        normalized = message.lower()

        if "usa actualizar_retroalimentacion" in normalized:
            st.session_state[sent_key] = True
            st.session_state[notice_key] = False
            st.warning("Ya existe una retroalimentación previa. A partir de ahora solo puedes actualizarla.")
            st.rerun()

        if "no existe retroalimentacion" in normalized:
            st.warning("No existe retroalimentación previa para actualizar. Primero envía una inicial.")
            st.session_state[sent_key] = False
            return

        st.error(message)


def render() -> None:
    app = SequentialLearningFlow()
    app.render()
