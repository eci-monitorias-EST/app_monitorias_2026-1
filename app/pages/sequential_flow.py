from __future__ import annotations

from datetime import datetime
from typing import Callable

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from components.style import inject_global_styles
from domain.models import ExerciseOption, ExerciseProgress, ParticipantRecord
from services.modeling import DatasetBundle
from services.app_container import get_container
from services.comment_events import COMMENT_TYPE_LABELS
from services.profile_constraints import (
    DEFAULT_AGE,
    GRADE_OPTIONS,
    MAX_AGE,
    MIN_AGE,
    SEX_OPTIONS,
    clamp_age,
    validate_profile_fields,
)
from services.sequential_flow_state import FlowContext, build_sequential_flow_state_machine
from services.sequential_flow_state import derive_exercise_flow_state, derive_max_unlocked_step
from services.submission_validation import SubmissionValidationService


class SequentialLearningFlow:
    def __init__(self) -> None:
        self.container = get_container()
        self.validator: SubmissionValidationService = self.container.submission_validation
        self.state_machine = build_sequential_flow_state_machine()
        self._init_state()

    def _init_state(self) -> None:
        st.session_state.setdefault("current_step", 1)
        st.session_state.setdefault("max_unlocked_step", 1)
        st.session_state.setdefault("participant_id", None)
        st.session_state.setdefault("access_code", "")
        st.session_state.setdefault("selected_exercise", None)
        st.session_state.setdefault("exercise_step_state", {})
        st.session_state.setdefault("prediction_cache", None)
        st.session_state.setdefault("data_consent", None)

    @st.dialog("Autorización de tratamiento de datos")
    def _consent_dialog(self) -> None:
        st.write(
            "Esta recolección se realiza con fines académicos. "
            "De acuerdo con la Ley 1581 de 2012 en Colombia, el tratamiento de datos personales "
            "requiere autorización previa, expresa e informada del titular."
        )
        accepted = st.checkbox(
            "He leído la información y autorizo el tratamiento de mis datos para este ejercicio académico.",
            key="consent_checkbox_flow",
        )
        reject_col, accept_col = st.columns(2)
        with reject_col:
            if st.button("No autorizo", use_container_width=True):
                st.session_state["data_consent"] = False
                st.rerun()
        with accept_col:
            if st.button("Autorizo", type="primary", use_container_width=True, disabled=not accepted):
                st.session_state["data_consent"] = True
                st.rerun()

    def _current_record(self) -> ParticipantRecord | None:
        participant_id = st.session_state.get("participant_id")
        if not participant_id:
            return None
        return self.container.sessions.get_record(participant_id)

    def _current_bundle(self) -> DatasetBundle | None:
        selected = st.session_state.get("selected_exercise")
        if not selected:
            return None
        return self.container.catalog.get_bundle(selected)

    @staticmethod
    def _exercise_progress(
        record: ParticipantRecord | None, exercise: str
    ) -> ExerciseProgress | None:
        return record.exercise_progress.get(exercise) if record else None

    def _build_flow_context(self) -> FlowContext:
        return FlowContext(
            record=self._current_record(),
            has_meaningful_text=self.validator.has_meaningful_learning_text,
        )

    def _save_validated_progress_text(
        self,
        *,
        participant_id: str,
        exercise: str,
        field_name: str,
        text: str,
        field_label: str,
    ) -> bool:
        validation = self.validator.validate_learning_text(text, field_label=field_label)
        if not validation.is_valid:
            st.warning(validation.message)
            return False
        self.container.sessions.save_progress(
            participant_id,
            exercise,
            {field_name: text.strip()},
        )
        return True

    def render(self) -> None:
        inject_global_styles()
        self._sync_flow_state_with_selected_exercise()
        step = self.state_machine.get_step(st.session_state["current_step"])
        self._render_sidebar()
        st.progress(
            step.id / self.state_machine.total_steps,
            text=f"Paso {step.id} de {self.state_machine.total_steps}",
        )
        render_method: Callable[[], None] = getattr(self, step.renderer_name)
        render_method()
        self._render_navigation(step.id)

    def _sync_flow_state_with_selected_exercise(self) -> None:
        record = self._current_record()
        exercise = st.session_state.get("selected_exercise")

        if exercise and record is not None and record.selected_exercise == exercise:
            exercise_step_state = st.session_state["exercise_step_state"]
            base_state = derive_exercise_flow_state(
                record,
                self.validator.has_meaningful_learning_text,
            )
            requested_step = int(st.session_state.get("current_step", base_state.current_step))
            saved_current_step = int(
                exercise_step_state.get(exercise, {}).get("current_step", base_state.current_step)
            )
            if requested_step <= 3:
                current_step = requested_step
            elif saved_current_step <= 3:
                current_step = saved_current_step
            else:
                current_step = min(saved_current_step, base_state.max_unlocked_step)
            exercise_step_state[exercise] = {"current_step": current_step}
            st.session_state["current_step"] = current_step
            st.session_state["max_unlocked_step"] = base_state.max_unlocked_step
            return

        st.session_state["max_unlocked_step"] = derive_max_unlocked_step(
            record,
            self.validator.has_meaningful_learning_text,
        )
        st.session_state["current_step"] = min(
            st.session_state["current_step"],
            st.session_state["max_unlocked_step"],
        )

    def _set_current_step(self, step_id: int) -> None:
        st.session_state["current_step"] = step_id
        exercise = st.session_state.get("selected_exercise")
        if exercise and step_id >= 4:
            st.session_state["exercise_step_state"][exercise] = {"current_step": step_id}

    def _switch_selected_exercise(self, record: ParticipantRecord, exercise: str) -> None:
        current_exercise = st.session_state.get("selected_exercise")
        if current_exercise:
            self._set_current_step(st.session_state["current_step"])

        self.container.sessions.select_exercise(record.participant_id, exercise)
        st.session_state["selected_exercise"] = exercise

        refreshed_record = self.container.sessions.get_record(record.participant_id)
        if refreshed_record is None:
            raise ValueError("No fue posible recargar la sesión después de cambiar el ejercicio.")

        exercise_state = derive_exercise_flow_state(
            refreshed_record,
            self.validator.has_meaningful_learning_text,
        )
        saved_step = int(
            st.session_state["exercise_step_state"].get(exercise, {}).get(
                "current_step",
                exercise_state.current_step,
            )
        )
        self._set_current_step(max(4, min(saved_step, exercise_state.max_unlocked_step)))
        st.session_state["max_unlocked_step"] = exercise_state.max_unlocked_step
        st.session_state["prediction_cache"] = None

    def _render_sidebar(self) -> None:
        current_step = st.session_state["current_step"]
        record = self._current_record()
        with st.sidebar:
            st.markdown("## Flujo Bankify")
            for step in self.state_machine.steps:
                is_current = step.id == current_step
                can_open = step.id <= st.session_state["max_unlocked_step"]
                css = "step-chip active" if is_current else "step-chip"
                st.markdown(f"<span class='{css}'>{step.id}. {step.title}</span>", unsafe_allow_html=True)
                if st.button(
                    "Abrir" if not is_current else "Actual",
                    key=f"goto_step_{step.id}",
                    use_container_width=True,
                    disabled=(not can_open) or is_current,
                ):
                    self._set_current_step(step.id)
                    st.rerun()
            if record:
                st.divider()
                st.caption(f"Sesión: {record.public_alias}")
                if record.access_code_display:
                    st.caption(f"Código de acceso: {record.access_code_display}")
                exercise_label = (
                    ExerciseOption.LABELS[record.selected_exercise]
                    if record.selected_exercise
                    else "Pendiente"
                )
                st.caption(f"Ejercicio: {exercise_label}")

    def _render_navigation(self, step: int) -> None:
        back_col, next_col = st.columns(2)
        with back_col:
            if st.button("Atrás", use_container_width=True, disabled=step == 1):
                self._set_current_step(self.state_machine.previous_step_id(step))
                st.rerun()
        with next_col:
            if step == self.state_machine.total_steps:
                return
            next_step = self.state_machine.next_step_id(step, self._build_flow_context())
            can_next = next_step is not None
            if st.button("Siguiente", use_container_width=True, disabled=not can_next):
                assert next_step is not None
                self._set_current_step(next_step)
                st.rerun()
            if not can_next:
                st.caption("Completa el entregable del paso actual para continuar.")

    def _render_welcome(self) -> None:
        st.markdown(
            """
            <section class="bankify-hero">
                <h1>Bankify Analytics Lab</h1>
                <p>
                    Eres parte del equipo de Ingeniería Estadística de Bankify. Tu misión es estudiar datos reales,
                    argumentar hallazgos y explicar decisiones de modelos que ayudan a aprobar créditos y anticipar mora.
                </p>
                <div>
                    <span class="bankify-pill">Storytelling académico</span>
                    <span class="bankify-pill">Modelos explicables</span>
                    <span class="bankify-pill">Comentarios anónimos</span>
                </div>
            </section>
            """,
            unsafe_allow_html=True,
        )
        col1, col2, col3 = st.columns(3)
        for column, title, body in [
            (col1, "Reto 1", "Determinar si un perfil crediticio merece aprobación o revisión adicional."),
            (col2, "Reto 2", "Estimar el riesgo de mora y justificarlo con evidencia cuantitativa."),
            (col3, "Reto 3", "Comparar tus interpretaciones con comentarios anónimos de otros estudiantes."),
        ]:
            with column:
                st.markdown(
                    f"<div class='bankify-card'><h4>{title}</h4><p>{body}</p></div>",
                    unsafe_allow_html=True,
                )
        st.info(
            "El sistema genera automáticamente un código de acceso por sesión. Guárdalo: es el mecanismo oficial para retomar tu avance."
        )

    def _render_data_collection(self) -> None:
        record = self._current_record()
        st.title("Recolección de datos y recuperación de sesión")
        st.write(
            "Crea una nueva sesión y el sistema te entregará un código de acceso único. "
            "Para reanudar, ingresa ese código."
        )
        if record:
            st.success(f"Sesión recuperada: {record.public_alias}")
            if record.access_code_display:
                st.markdown("#### Código de acceso de esta sesión")
                st.code(record.access_code_display)
                st.caption("Guárdalo. Este código es la forma oficial de reanudar la sesión.")
            st.json(record.profile)
            return
        if st.session_state["data_consent"] is not True:
            self._consent_dialog()
            if st.session_state["data_consent"] is False:
                st.error("No autorizaste el tratamiento de datos. No es posible continuar con el registro.")
                if st.button("Volver a mostrar autorización"):
                    st.session_state["data_consent"] = None
                    st.rerun()
            else:
                st.info("Debes autorizar el tratamiento de datos para habilitar el formulario.")
            return
        with st.expander("Reanudar una sesión existente", expanded=True):
            with st.form("participant_recovery_form"):
                access_code = st.text_input(
                    "Código de acceso",
                    help="Ingresa el código que recibiste al crear la sesión.",
                )
                recovery_submitted = st.form_submit_button("Reanudar sesión")
            if recovery_submitted:
                recovered = self.container.sessions.recover(access_code)
                if recovered is None:
                    st.error("No encontramos una sesión con ese código. Verifica el código e intentá de nuevo.")
                    return
                st.session_state["participant_id"] = recovered.participant_id
                st.session_state["access_code"] = recovered.access_code_display
                if recovered.selected_exercise:
                    st.session_state["selected_exercise"] = recovered.selected_exercise
                st.success(f"Sesión recuperada: {recovered.public_alias}")
                st.rerun()
        st.divider()
        st.markdown("### Crear una nueva sesión")
        with st.form("participant_login_form"):
            nombre = st.text_input("Nombre")
            sexo = st.selectbox("Sexo", SEX_OPTIONS)
            colegio = st.text_input("Colegio")
            edad = st.number_input("Edad", min_value=MIN_AGE, max_value=MAX_AGE, value=DEFAULT_AGE, step=1)
            grado = st.selectbox("Grado o nivel", GRADE_OPTIONS)
            interes_carrera = st.text_area("¿Qué te llamó la atención de Ingeniería Estadística?")
            matematicas_avanzadas = st.text_area("¿Qué es lo más avanzado de matemáticas que has visto?")
            submitted = st.form_submit_button("Crear sesión y generar código", type="primary")
        if submitted:
            if not all(
                [
                    nombre.strip(),
                    sexo.strip(),
                    colegio.strip(),
                    grado.strip(),
                    interes_carrera.strip(),
                    matematicas_avanzadas.strip(),
                ]
            ):
                st.warning("Completa todos los campos obligatorios de la sesión.")
                return
            try:
                validate_profile_fields(sexo=sexo, edad=int(edad), grado=grado)
            except ValueError as exc:
                st.warning(str(exc))
                return
            record = self.container.sessions.start_session(
                profile={
                    "Dia": datetime.now().strftime("%Y-%m-%d"),
                    "nombre": nombre.strip(),
                    "sexo": sexo,
                    "colegio": colegio.strip(),
                    "edad": clamp_age(int(edad)),
                    "grado": grado,
                    "interes_carrera": interes_carrera.strip(),
                    "matematicas_avanzadas": matematicas_avanzadas.strip(),
                },
            )
            st.session_state["participant_id"] = record.participant_id
            st.session_state["access_code"] = record.access_code_display
            if record.selected_exercise:
                st.session_state["selected_exercise"] = record.selected_exercise
            st.success(
                f"Sesión activa con alias anónimo {record.public_alias}. Guarda tu código para retomarla después."
            )
            st.rerun()

    def _render_exercise_choice(self) -> None:
        record = self._current_record()
        if not record:
            st.warning("Primero activa o recupera tu sesión.")
            return
        st.title("Elige tu ejercicio")
        columns = st.columns(2)
        options = [
            (
                ExerciseOption.CREDIT_APPROVAL,
                "Aprobación de crédito",
                "Analiza el perfil del solicitante y determina si Bankify debería aprobar o revisar la solicitud.",
            ),
            (
                ExerciseOption.DEFAULT_RISK,
                "Probabilidad de mora",
                "Estudia historiales de pago para anticipar incumplimiento y explicar el riesgo de mora.",
            ),
        ]
        for column, (key, title, description) in zip(columns, options):
            with column:
                st.markdown(
                    f"<div class='bankify-card'><h3>{title}</h3><p>{description}</p></div>",
                    unsafe_allow_html=True,
                )
                if st.button(f"Seleccionar {title}", key=f"select_{key}", use_container_width=True):
                    self._switch_selected_exercise(record, key)
                    st.success(f"Ejercicio seleccionado: {title}")
                    st.rerun()
        if record.selected_exercise:
            st.info(f"Selección actual: {ExerciseOption.LABELS[record.selected_exercise]}")

    def _render_dataset_view(self) -> None:
        record = self._current_record()
        bundle = self._current_bundle()
        if not record or bundle is None:
            st.warning("Selecciona un ejercicio antes de continuar.")
            return
        st.title("Conozcamos a nuestros clientes")
        st.caption(bundle.source_note)
        st.dataframe(bundle.df.head(25), use_container_width=True, height=420)
        descriptor_df = pd.DataFrame([descriptor.to_dict() for descriptor in bundle.descriptors])
        st.markdown("### Descripción de variables")
        st.dataframe(descriptor_df[["label", "official_name", "description", "variable_type"]], use_container_width=True)
        progress = self._exercise_progress(record, bundle.exercise)
        with st.form("dataset_comment_form"):
            comment = st.text_area(
                "¿Qué te sugiere este dataset?",
                value=progress.dataset_comment if progress else "",
                height=140,
            )
            submitted = st.form_submit_button("Guardar comentario")
        if submitted:
            if self._save_validated_progress_text(
                participant_id=record.participant_id,
                exercise=bundle.exercise,
                field_name="dataset_comment",
                text=comment,
                field_label="comentario sobre el dataset",
            ):
                st.success("Comentario guardado sin duplicar el registro.")

    def _render_dashboard(self) -> None:
        record = self._current_record()
        bundle = self._current_bundle()
        if not record or bundle is None:
            return
        st.title("Exploración y dashboard")
        df = bundle.df.copy()
        numeric_cols = df.select_dtypes(include="number").columns.tolist()
        cat_cols = [column for column in bundle.features if column not in numeric_cols]
        left, right = st.columns([1.2, 1.8])
        with left:
            target_filter = st.selectbox("Variable para gráfico principal", numeric_cols[: min(8, len(numeric_cols))])
            cat_filter = st.selectbox("Categoría para segmentar", cat_cols[: min(8, len(cat_cols))] or [bundle.target])
        with right:
            st.markdown("### Instrucciones")
            st.write(
                "Explora distribuciones, compara segmentos y redacta un hallazgo estadístico. "
                "Piensa cómo ese hallazgo impactaría la decisión de Bankify."
            )
        chart1, chart2 = st.columns(2)
        with chart1:
            st.plotly_chart(px.histogram(df, x=target_filter, title=f"Histograma de {target_filter}"), use_container_width=True)
            if cat_cols:
                st.plotly_chart(
                    px.box(df, x=cat_filter, y=target_filter, title=f"Boxplot de {target_filter} por {cat_filter}"),
                    use_container_width=True,
                )
        with chart2:
            if cat_cols:
                pie_counts = df[cat_filter].astype(str).value_counts().head(8).reset_index()
                pie_counts.columns = [cat_filter, "count"]
                st.plotly_chart(
                    px.pie(pie_counts, names=cat_filter, values="count", title=f"Composición de {cat_filter}"),
                    use_container_width=True,
                )
                st.plotly_chart(
                    px.bar(
                        df.groupby(cat_filter)[target_filter].mean().reset_index(),
                        x=cat_filter,
                        y=target_filter,
                        title=f"Promedio de {target_filter} por {cat_filter}",
                    ),
                    use_container_width=True,
                )
        if len(numeric_cols) >= 2:
            st.plotly_chart(
                px.scatter(
                    df,
                    x=numeric_cols[0],
                    y=numeric_cols[1],
                    color=df[cat_filter].astype(str) if cat_cols else None,
                    title="Dispersión exploratoria",
                ),
                use_container_width=True,
            )
        progress = self._exercise_progress(record, bundle.exercise)
        with st.form("analytics_comment_form"):
            comment = st.text_area(
                "¿Qué hallazgo relevante encontraste?",
                value=progress.analytics_comment if progress else "",
                height=140,
            )
            submitted = st.form_submit_button("Guardar interpretación")
        if submitted:
            if self._save_validated_progress_text(
                participant_id=record.participant_id,
                exercise=bundle.exercise,
                field_name="analytics_comment",
                text=comment,
                field_label="hallazgo analítico",
            ):
                st.success("Interpretación guardada.")

    def _coerce_input(self, descriptor, value: str):
        if descriptor.variable_type == "numeric":
            return float(value) if "." in value else int(value)
        return value

    def _render_prediction(self) -> None:
        record = self._current_record()
        bundle = self._current_bundle()
        if not record or bundle is None:
            return
        st.title("Predicción del modelo")
        st.caption("La explicación pedagógica se deriva de señales locales tipo LIME/SHAP y un agente textual desacoplado.")
        descriptor_map = {descriptor.key: descriptor for descriptor in bundle.descriptors}
        with st.form("prediction_form"):
            features = {}
            for feature_name in bundle.features:
                descriptor = descriptor_map.get(feature_name)
                label = descriptor.label if descriptor else feature_name
                help_text = descriptor.description if descriptor else f"Variable {feature_name} del modelo."
                series = bundle.df[feature_name]
                is_numeric = pd.api.types.is_numeric_dtype(series)
                if is_numeric:
                    value = st.number_input(
                        label,
                        value=float(series.median()),
                        help=help_text,
                    )
                    features[feature_name] = value
                else:
                    options = sorted(series.astype(str).unique().tolist())
                    features[feature_name] = st.selectbox(
                        label,
                        options=options,
                        help=help_text,
                    )
            submitted = st.form_submit_button("Ejecutar predicción", type="primary")
        if submitted:
            result = self.container.predictions.predict(bundle.exercise, features)
            st.session_state["prediction_cache"] = result.to_dict()
            self.container.sessions.save_progress(
                record.participant_id,
                bundle.exercise,
                {
                    "prediction_inputs": features,
                    "prediction_output": result.to_dict(),
                },
            )

        prediction_cache = st.session_state.get("prediction_cache")
        if prediction_cache:
            progress = self._exercise_progress(record, bundle.exercise)
            st.metric("Resultado", prediction_cache["label"], f"{prediction_cache['probability']:.1%}")
            col1, col2 = st.columns(2)
            with col1:
                lime_df = pd.DataFrame(prediction_cache["local_explanations"]["lime"]["items"])
                st.plotly_chart(
                    px.bar(lime_df.head(8), x="impact", y="feature", orientation="h", title="LIME local"),
                    use_container_width=True,
                )
            with col2:
                shap_df = pd.DataFrame(prediction_cache["local_explanations"]["shap_local"]["items"])
                st.plotly_chart(
                    px.bar(shap_df.head(8), x="impact", y="feature", orientation="h", title="SHAP local"),
                    use_container_width=True,
                )
            global_df = pd.DataFrame(prediction_cache["global_explanations"]["shap_global"]["items"])
            st.plotly_chart(
                px.bar(global_df.head(10), x="importance", y="feature", orientation="h", title="SHAP global"),
                use_container_width=True,
            )
            st.info(prediction_cache["pedagogical_summary"])
            with st.form("prediction_reflection_form"):
                reflection = st.text_area(
                    "¿Qué entendiste de la explicación del modelo?",
                    value=progress.prediction_reflection if progress else "",
                    height=120,
                )
                submitted = st.form_submit_button("Guardar comprensión")
            if submitted:
                if self._save_validated_progress_text(
                    participant_id=record.participant_id,
                    exercise=bundle.exercise,
                    field_name="prediction_reflection",
                    text=reflection,
                    field_label="reflexión sobre la predicción",
                ):
                    st.success("Reflexión guardada.")

    def _render_comments_projection(self) -> None:
        record = self._current_record()
        bundle = self._current_bundle()
        if not record or bundle is None:
            return
        st.title("Visualización 3D de comentarios")
        try:
            projection = self.container.comments.build_projection_for_exercise(
                bundle.exercise,
                record.participant_id,
            )
        except RuntimeError as exc:
            st.error(str(exc))
            st.caption(
                "La visualización 3D requiere embeddings configurados (MiniLM o fastText de respaldo) "
                "y reducción UMAP reales. Verifica la configuración local y vuelve a ejecutar."
            )
            return
        if not projection["points"]:
            st.info("Aún no hay comentarios completados para este ejercicio. Termina una sesión completa para alimentar el gráfico.")
            return
        df = pd.DataFrame(projection["points"])
        color_map = {
            "dataset_comment": "#60a5fa",
            "analytics_comment": "#34d399",
            "prediction_reflection": "#f59e0b",
        }
        symbol_map = {
            "dataset_comment": "circle",
            "analytics_comment": "square",
            "prediction_reflection": "diamond",
        }
        fig = go.Figure()
        for comment_type, label in COMMENT_TYPE_LABELS.items():
            for is_current_user, trace_suffix in ((False, "Otros"), (True, "Tu sesión")):
                subset = df[(df["comment_type"] == comment_type) & (df["current_user"] == is_current_user)]
                if subset.empty:
                    continue
                fig.add_trace(
                    go.Scatter3d(
                        x=subset["x"],
                        y=subset["y"],
                        z=subset["z"],
                        mode="markers",
                        marker=dict(
                            size=13 if is_current_user else 6,
                            color=color_map.get(comment_type, "#94a3b8"),
                            opacity=0.95 if is_current_user else 0.55,
                            symbol=symbol_map.get(comment_type, "circle"),
                            line=dict(
                                color="#0f172a" if is_current_user else "rgba(15,23,42,0.15)",
                                width=4 if is_current_user else 1,
                            ),
                        ),
                        text=subset["comment"],
                        customdata=subset[["public_alias", "comment_type_label"]].to_numpy(),
                        hovertemplate=(
                            "<b>%{customdata[0]}</b><br>"
                            "Tipo: %{customdata[1]}<br>"
                            "%{text}<extra></extra>"
                        ),
                        name=f"{label} · {trace_suffix}",
                    )
                )
        fig.update_layout(title=f"Comentarios anónimos - {bundle.label}", height=650)
        st.plotly_chart(fig, use_container_width=True)
        st.caption(
            f"Embeddings: {projection['embedding_provider']} | Reducción: {projection['reduction_provider']}"
        )
        st.dataframe(
            df[["public_alias", "comment_type_label", "comment", "current_user"]],
            use_container_width=True,
        )

    def _render_final_feedback(self) -> None:
        record = self._current_record()
        bundle = self._current_bundle()
        if not record or bundle is None:
            return
        st.title("Retroalimentación final")
        st.write("Ejercicio creado por los monitores de Ingeniería Estadística.")
        progress = self._exercise_progress(record, bundle.exercise)
        previous = progress.feedback if progress else None
        with st.form("feedback_form"):
            rating = st.slider("Califica la experiencia", min_value=0, max_value=5, value=previous.rating if previous else 4)
            summary = st.text_area("Resumen de la experiencia", value=previous.summary if previous else "")
            missing_topics = ""
            improvement_ideas = ""
            if rating < 3:
                missing_topics = st.text_area(
                    "¿Qué faltó para que la experiencia fuera mejor?",
                    value=previous.missing_topics if previous else "",
                )
                improvement_ideas = st.text_area(
                    "¿Qué deberíamos mejorar?",
                    value=previous.improvement_ideas if previous else "",
                )
            submitted = st.form_submit_button("Guardar y finalizar", type="primary")
        if submitted:
            validation = self.validator.validate_learning_text(
                summary,
                field_label="resumen de la experiencia",
            )
            if not validation.is_valid:
                st.warning(validation.message)
                return
            self.container.sessions.save_feedback(
                record.participant_id,
                bundle.exercise,
                {
                    "rating": rating,
                    "summary": summary.strip(),
                    "missing_topics": missing_topics.strip(),
                    "improvement_ideas": improvement_ideas.strip(),
                },
            )
            self.container.sessions.complete_activity(record.participant_id, bundle.exercise)
            st.success("Actividad finalizada. Tus comentarios ya hacen parte de la visualización anónima del ejercicio.")


def render() -> None:
    SequentialLearningFlow().render()
