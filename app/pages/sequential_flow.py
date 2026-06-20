from __future__ import annotations

from datetime import datetime
from typing import Callable

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from components.style import inject_global_styles
from domain.models import ExerciseOption, ExerciseProgress, ModelEvaluationResult, ParticipantRecord
from pages.eda_dashboard import render_eda_dashboard
from services.modeling import DatasetBundle
from services.app_container import get_container
from services.comment_events import COMMENT_TYPE_LABELS
from services.dashboard_sections import combine_sections, split_sections
from services.sequential_flow_state import FlowContext, build_sequential_flow_state_machine
from services.sequential_flow_state import derive_exercise_flow_state, derive_max_unlocked_step
from services.submission_validation import SubmissionValidationService


_EDA_DASHBOARD_STEP = 4
_EDA_DASHBOARD_CHAPTERS = 3


def _html(markup: str) -> None:
    """Renderiza HTML aplanado en una sola línea.

    Markdown interpreta como bloque de código cualquier línea con 4+ espacios
    de indentación, por lo que el HTML multilínea generado con f-strings se
    filtraría como texto crudo.
    """
    st.markdown(" ".join(line.strip() for line in markup.splitlines()), unsafe_allow_html=True)


def _render_simulation_card(exercise_label: str, prediction_cache: dict) -> None:
    favorable_labels = {"Aprobado", "Baja probabilidad de mora"}
    label = prediction_cache["label"]
    status_class = "good" if label in favorable_labels else "warn"
    provider_label = prediction_cache["provider"].replace("_", " ").title()
    probability_pct = prediction_cache["probability"] * 100
    _html(
        f"""
        <div class="bankify-simulation-card">
            <span class="bankify-simulation-tag">Resultado de la simulación</span>
            <span class="bankify-simulation-label">Recomendación · {exercise_label}</span>
            <p class="bankify-simulation-value">
                <span class="bankify-status-dot {status_class}"></span>{label}
            </p>
            <div class="bankify-simulation-confidence-row">
                <span>Puntaje de confianza</span>
                <span>{prediction_cache['probability']:.1%}</span>
            </div>
            <div class="bankify-simulation-track">
                <span style="width: {probability_pct:.1f}%"></span>
            </div>
            <span class="bankify-simulation-badge">{provider_label}</span>
        </div>
        """
    )


def _render_kpi_stack(evaluation: ModelEvaluationResult) -> None:
    metrics = [
        ("Exactitud", evaluation.accuracy, "De todas las predicciones, qué porcentaje fue correcto."),
        ("Precisión", evaluation.precision, "De los casos marcados como positivos, qué porcentaje lo era de verdad."),
        ("Exhaustividad (Recall)", evaluation.recall, "De los casos positivos reales, qué porcentaje detectó el modelo."),
        ("F1-Score", evaluation.f1, "Balance entre precision y recall."),
    ]
    cards = "".join(
        f"""
        <div class="bankify-kpi-card">
            <span class="bankify-kpi-label">{label}</span>
            <span class="bankify-kpi-value">{value:.1%}</span>
            <span class="bankify-kpi-hint">{hint}</span>
        </div>
        """
        for label, value, hint in metrics
    )
    _html(f"<div class='bankify-kpi-stack'>{cards}</div>")


def _render_results_socialization(evaluation: ModelEvaluationResult) -> None:
    _html(
        f"""
        <div class="bankify-section-card-header">
            <span class="bankify-section-icon">&#9670;</span>
            <h2>Socialización de resultados</h2>
        </div>
        <p class="bankify-model-intro">
            Resultados del modelo <b>{evaluation.model_name}</b> (el mismo construido en los
            notebooks de este ejercicio) medidos sobre {evaluation.test_size:,} casos de prueba
            que el modelo no usó para aprender.
        </p>
        """
    )

    negative_label, positive_label = evaluation.class_labels
    (tn, fp), (fn, tp) = evaluation.confusion_matrix
    _html("<p class='bankify-cm-tag'>Matriz de confusión (conjunto de prueba)</p>")
    _html(
        f"""
        <div class="bankify-cm-wrapper">
            <table class="bankify-cm-table">
                <tr>
                    <th></th>
                    <th>Predicho: {negative_label}</th>
                    <th>Predicho: {positive_label}</th>
                </tr>
                <tr>
                    <th>Real: {negative_label}</th>
                    <td class="bankify-cm-good">{tn}</td>
                    <td class="bankify-cm-bad">{fp}</td>
                </tr>
                <tr>
                    <th>Real: {positive_label}</th>
                    <td class="bankify-cm-bad">{fn}</td>
                    <td class="bankify-cm-good">{tp}</td>
                </tr>
            </table>
        </div>
        """
    )

    if evaluation.coefficient_importance is not None:
        _html("<p class='bankify-cm-tag'>Coeficientes del modelo (betas)</p>")
        top_items = list(reversed(evaluation.coefficient_importance[:8]))
        bar_colors = ["#006bd6" if item["coefficient"] >= 0 else "#be123c" for item in top_items]
        fig = go.Figure(
            go.Bar(
                x=[item["coefficient"] for item in top_items],
                y=[item["feature"] for item in top_items],
                orientation="h",
                marker_color=bar_colors,
            )
        )
        fig.add_vline(x=0, line_width=1, line_color="#94a3b8")
        fig.update_layout(
            margin=dict(l=10, r=10, t=10, b=10),
            height=340,
            xaxis_title="Coeficiente (beta) sobre la variable estandarizada",
        )
        st.plotly_chart(fig, use_container_width=True)
        st.caption(
            "Un beta positivo (azul) aumenta la probabilidad de la clase positiva; "
            "un beta negativo (rojo) la reduce. Por ser un modelo de regresión logística, "
            "estos coeficientes son directamente interpretables."
        )
    else:
        _html("<p class='bankify-cm-tag'>Variables con mayor peso en la predicción (SHAP)</p>")
        top_items = list(reversed(evaluation.shap_importance[:8]))
        fig = go.Figure(
            go.Bar(
                x=[item["importance"] for item in top_items],
                y=[item["feature"] for item in top_items],
                orientation="h",
                marker_color="#006bd6",
            )
        )
        fig.update_layout(
            margin=dict(l=10, r=10, t=10, b=10),
            height=340,
            xaxis_title="Impacto medio en la predicción (|SHAP|)",
        )
        st.plotly_chart(fig, use_container_width=True)


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
        st.session_state.setdefault("profile_continue_requested", False)
        st.session_state.setdefault("prediction_cache", None)
        st.session_state.setdefault("data_consent", None)
        st.session_state.setdefault("eda_chapter", 1)

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

    def _exercise_completion_percent(self, record: ParticipantRecord, exercise: str) -> int:
        progress = self._exercise_progress(record, exercise)
        if progress is None:
            return 0
        completed = 0
        if self.validator.has_meaningful_learning_text(progress.dataset_comment):
            completed += 1
        if self.validator.has_meaningful_learning_text(progress.analytics_comment):
            completed += 1
        if progress.prediction_output and self.validator.has_meaningful_learning_text(progress.prediction_reflection):
            completed += 1
        if progress.feedback is not None or progress.completed_at:
            completed += 1
        return int(round((completed / 4) * 100))

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
        if step.id not in {1, 2}:
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
            if not bool(st.session_state.get("profile_continue_requested", False)):
                current_step = min(requested_step, 2)
            elif requested_step <= 2:
                current_step = requested_step
            elif saved_current_step <= 2:
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
        if step_id >= 3:
            st.session_state["profile_continue_requested"] = True
        exercise = st.session_state.get("selected_exercise")
        if exercise and step_id >= 3:
            st.session_state["exercise_step_state"][exercise] = {"current_step": step_id}

    def _switch_selected_exercise(self, record: ParticipantRecord, exercise: str) -> None:
        current_exercise = st.session_state.get("selected_exercise")
        if current_exercise and st.session_state["current_step"] >= 3:
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
        self._set_current_step(max(3, min(saved_step, exercise_state.max_unlocked_step)))
        st.session_state["max_unlocked_step"] = exercise_state.max_unlocked_step
        st.session_state["prediction_cache"] = None
        st.session_state["eda_chapter"] = 1

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
            if st.button("Atrás", type="primary", use_container_width=True, disabled=step == 1):
                if step == _EDA_DASHBOARD_STEP and st.session_state["eda_chapter"] > 1:
                    st.session_state["eda_chapter"] -= 1
                else:
                    previous_step = self.state_machine.previous_step_id(step)
                    if previous_step == _EDA_DASHBOARD_STEP:
                        st.session_state["eda_chapter"] = _EDA_DASHBOARD_CHAPTERS
                    self._set_current_step(previous_step)
                st.rerun()
        with next_col:
            if step == self.state_machine.total_steps:
                return
            if step == _EDA_DASHBOARD_STEP and st.session_state["eda_chapter"] < _EDA_DASHBOARD_CHAPTERS:
                if st.button("Siguiente", type="primary", use_container_width=True):
                    st.session_state["eda_chapter"] += 1
                    st.rerun()
                return
            next_step = self.state_machine.next_step_id(step, self._build_flow_context())
            can_next = next_step is not None
            if st.button("Siguiente", type="primary", use_container_width=True, disabled=not can_next):
                assert next_step is not None
                if next_step == _EDA_DASHBOARD_STEP:
                    st.session_state["eda_chapter"] = 1
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
                    Eres parte del equipo de Ingenier\u00eda Estad\u00edstica de Bankify. Tu misi\u00f3n es estudiar datos reales,
                    argumentar hallazgos y explicar decisiones de modelos que ayudan a aprobar cr\u00e9ditos y anticipar mora.
                </p>
                <div>
                    <span class="bankify-pill">Storytelling acad\u00e9mico</span>
                    <span class="bankify-pill">Modelos explicables</span>
                    <span class="bankify-pill">Comentarios an\u00f3nimos</span>
                </div>
            </section>
            """,
            unsafe_allow_html=True,
        )
        record = self._current_record()
        if record:
            st.success(f"Sesi\u00f3n activa: {record.public_alias}")
            if record.access_code_display:
                st.markdown("#### C\u00f3digo de acceso")
                st.code(record.access_code_display)
                st.caption("Gu\u00e1rdalo para retomar tu avance m\u00e1s adelante.")
            return

        _, form_col, _ = st.columns([1, 1.35, 1])
        with form_col:
            st.markdown(
                """
                <div class="bankify-access-heading">
                    <h2>Acceso</h2>
                    <p>Ingresa tus datos para comenzar</p>
                </div>
                """,
                unsafe_allow_html=True,
            )
            with st.form("welcome_access_form"):
                nombre = st.text_input("Nombre", placeholder="Ej. Alex Rivera")
                access_code = st.text_input(
                    "C\u00f3digo de acceso",
                    placeholder="Ingresa tu c\u00f3digo para retomar",
                    help="Usa este campo solo si ya tienes una sesi\u00f3n activa.",
                )
                st.caption("opcional si ya se tiene una sesi\u00f3n iniciada.")
                submitted = st.form_submit_button("Comenzar experiencia", type="primary", use_container_width=True)

        if not submitted:
            return

        if not nombre.strip():
            st.warning("Ingresa tu nombre para comenzar.")
            return

        profile = {
            "Dia": datetime.now().strftime("%Y-%m-%d"),
            "nombre": nombre.strip(),
        }
        if access_code.strip():
            recovered = self.container.sessions.recover(access_code)
            if recovered is None:
                st.error("No encontramos una sesi\u00f3n con ese c\u00f3digo. Verifica el c\u00f3digo e int\u00e9ntalo de nuevo.")
                return
            record = self.container.sessions.login_or_resume(access_code, profile)
        else:
            record = self.container.sessions.start_session(profile=profile)

        st.session_state["participant_id"] = record.participant_id
        st.session_state["access_code"] = record.access_code_display
        if record.selected_exercise:
            st.session_state["selected_exercise"] = record.selected_exercise
        self._set_current_step(2)
        st.rerun()

    def _render_data_collection(self) -> None:
        record = self._current_record()
        if not record:
            st.warning("Primero activa o recupera tu sesi\u00f3n en la bienvenida.")
            return

        profile_name = str(record.profile.get("nombre", "")).strip() or record.public_alias
        st.markdown(
            f"""
            <section class="bankify-profile-hero">
                <div>
                    <p class="bankify-profile-kicker">Bienvenida, {profile_name}</p>
                    <span class="bankify-code-pill">C\u00f3digo: {record.access_code_display}</span>
                    <p class="bankify-profile-copy">
                        Tu sesi\u00f3n est\u00e1 activa. Escoge el proceso que deseas desarrollar hoy y contin\u00faa
                        con tu an\u00e1lisis de riesgo en el laboratorio de simulaci\u00f3n bancaria.
                    </p>
                </div>
            </section>
            """,
            unsafe_allow_html=True,
        )

        def continue_to_dataset(exercise: str) -> None:
            st.session_state["profile_continue_requested"] = True
            self._switch_selected_exercise(record, exercise)
            self._set_current_step(3)
            st.rerun()

        st.markdown("### Mis Procesos")
        header_col, history_col = st.columns([1, 1])
        with header_col:
            st.caption("Estado actual de tus m\u00f3dulos de an\u00e1lisis financiero.")
            st.caption("Escoge el proceso que deseas desarrollar hoy.")
        with history_col:
            st.markdown("<p class='bankify-history-link'>Ver historial \u2192</p>", unsafe_allow_html=True)

        options = [
            (ExerciseOption.CREDIT_APPROVAL, "Aprobaci\u00f3n de cr\u00e9dito", "\u25a3"),
            (ExerciseOption.DEFAULT_RISK, "Probabilidad de mora", "\u2198"),
        ]
        columns = st.columns(2)
        for column, (exercise, title, icon) in zip(columns, options):
            percent = self._exercise_completion_percent(record, exercise)
            status = "En progreso" if percent > 0 else "Reci\u00e9n iniciado"
            status_class = "progress" if percent > 0 else "new"
            with column:
                st.markdown(
                    f"""
                    <article class="bankify-process-card">
                        <div class="bankify-process-top">
                            <span class="bankify-process-icon">{icon}</span>
                            <span class="bankify-process-status {status_class}">{status}</span>
                        </div>
                        <h3>{title}</h3>
                        <div class="bankify-progress-row">
                            <span>Progreso del m\u00f3dulo</span>
                            <strong>{percent}%</strong>
                        </div>
                        <div class="bankify-progress-track">
                            <span style="width: {percent}%"></span>
                        </div>
                    </article>
                    """,
                    unsafe_allow_html=True,
                )
                if st.button("Continuar", key=f"continue_{exercise}", type="primary", use_container_width=True):
                    continue_to_dataset(exercise)
        return

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

        exercise_label = ExerciseOption.LABELS[bundle.exercise]
        st.markdown(
            f"""
            <section class="bankify-data-hero">
                <div>
                    <h1>Diccionario de Datos</h1>
                    <span class="bankify-filter-pill">Filtrado por: {exercise_label}</span>
                    <p>
                        Para realizar un análisis de riesgo efectivo, es fundamental comprender el origen
                        y la naturaleza de las variables que estamos procesando. A continuación, se detallan
                        las variables clave para este ejercicio de simulación bancaria.
                    </p>
                </div>
                <span class="bankify-book-icon">\u25f0</span>
            </section>
            """,
            unsafe_allow_html=True,
        )

        type_labels = {
            "numeric": "Numérico",
            "categorical": "Categórico",
        }
        table_rows = "\n".join(
            f"""
            <tr class="bankify-dictionary-row">
                <td class="bankify-dictionary-cell bankify-var-name">{descriptor.label}</td>
                <td class="bankify-dictionary-cell">{descriptor.description}</td>
                <td class="bankify-dictionary-cell"><span class="bankify-type-badge">{type_labels.get(descriptor.variable_type, descriptor.variable_type.title())}</span></td>
            </tr>
            """
            for descriptor in bundle.descriptors
        )
        _html(
            f"""
            <section class="bankify-dictionary-card">
                <header>
                    <span class="bankify-section-icon">◆</span>
                    <h2>{exercise_label}</h2>
                </header>
                <div class="bankify-dictionary-table-wrapper">
                    <table class="bankify-dictionary-table">
                        <thead>
                            <tr class="bankify-dictionary-head-row">
                                <th class="bankify-dictionary-head">Variable</th>
                                <th class="bankify-dictionary-head">Descripción</th>
                                <th class="bankify-dictionary-head">Tipo</th>
                            </tr>
                        </thead>
                        <tbody>
                            {table_rows}
                        </tbody>
                    </table>
                </div>
            </section>
            """
        )

        progress = self._exercise_progress(record, bundle.exercise)
        st.markdown("### \u00bfQu\u00e9 le sugiere el conjunto de datos?")
        st.caption("Utiliza este espacio para anotar tus hallazgos iniciales.")
        with st.form("dataset_comment_form"):
            comment = st.text_area(
                "\u00bfQu\u00e9 le sugiere el conjunto de datos?",
                value=progress.dataset_comment if progress else "",
                height=140,
                label_visibility="collapsed",
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

    def _save_dashboard_section(
        self, participant_id: str, exercise: str, chapter: int, text: str
    ) -> bool:
        validation = self.validator.validate_learning_text(
            text, field_label=f"respuesta de la pregunta {chapter}"
        )
        if not validation.is_valid:
            st.warning(validation.message)
            return False
        record = self.container.sessions.get_record(participant_id)
        progress = (
            record.exercise_progress.get(exercise) if record else None
        )
        sections = split_sections(progress.analytics_comment if progress else "")
        sections[chapter] = text.strip()
        self.container.sessions.save_progress(
            participant_id,
            exercise,
            {"analytics_comment": combine_sections(sections)},
        )
        return True

    def _render_dashboard(self) -> None:
        record = self._current_record()
        bundle = self._current_bundle()
        if not record or bundle is None:
            return
        progress = self._exercise_progress(record, bundle.exercise)
        section_values = split_sections(progress.analytics_comment if progress else "")

        def on_save(chapter: int, text: str) -> bool:
            return self._save_dashboard_section(
                record.participant_id, bundle.exercise, chapter, text
            )

        render_eda_dashboard(
            bundle,
            section_values=section_values,
            on_save=on_save,
            current_chapter=st.session_state["eda_chapter"],
        )

    def _coerce_input(self, descriptor, value: str):
        if descriptor.variable_type == "numeric":
            return float(value) if "." in value else int(value)
        return value

    def _render_prediction(self) -> None:
        record = self._current_record()
        bundle = self._current_bundle()
        if not record or bundle is None:
            return
        exercise_label = ExerciseOption.LABELS[bundle.exercise]
        _html(
            f"""
            <section class="bankify-prediction-hero">
                <div>
                    <h1>Predicción explicable</h1>
                    <p>Completa los valores del caso de prueba y obtén una predicción con explicación pedagógica basada en el modelo seleccionado.</p>
                </div>
                <div class="bankify-prediction-summary">
                    <h2>Ejercicio activo</h2>
                    <span class="bankify-metric-label">{exercise_label}</span>
                    <p class="bankify-metric-value">Modelo guiado por notebooks</p>
                    <p class="bankify-metric-subtitle">Usa la lógica del modelo de crédito y el árbol de decisión para mora.</p>
                    <span class="bankify-prediction-tag">Predicción con base académica</span>
                </div>
            </section>
            """
        )
        evaluation = self.container.model_evaluation.evaluate(bundle.exercise)
        descriptor_map = {descriptor.key: descriptor for descriptor in bundle.descriptors}
        left_col, right_col = st.columns([3, 2])

        with left_col:
            with st.container(border=True, key="prediction-input-card"):
                _html(
                    """
                    <div class="bankify-section-card-header">
                        <span class="bankify-section-icon">&#9638;</span>
                        <h2>Entrada de variables</h2>
                    </div>
                    <p class="bankify-model-intro">Ingresa los valores que definen el perfil y la situación financiera de la persona.</p>
                    """
                )
                with st.form("prediction_form"):
                    features = {}
                    field_cols = st.columns(2)
                    for index, feature_name in enumerate(bundle.features):
                        descriptor = descriptor_map.get(feature_name)
                        label = descriptor.label if descriptor else feature_name
                        help_text = descriptor.description if descriptor else f"Variable {feature_name} del modelo."
                        series = bundle.df[feature_name]
                        is_numeric = pd.api.types.is_numeric_dtype(series)
                        with field_cols[index % 2]:
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
                    submitted = st.form_submit_button("Ejecutar predicción", type="primary", use_container_width=True)
                if submitted:
                    result = self.container.predictions.predict(bundle.exercise, features)
                    st.session_state["prediction_cache"] = result.to_dict()
                    prediction_cache = result.to_dict()
                    self.container.sessions.save_progress(
                        record.participant_id,
                        bundle.exercise,
                        {
                            "prediction_inputs": features,
                            "prediction_output": result.to_dict(),
                        },
                    )
                else:
                    prediction_cache = st.session_state.get("prediction_cache")

        with right_col:
            if prediction_cache:
                _render_simulation_card(exercise_label, prediction_cache)
            else:
                st.info("Completa los campos del caso de prueba y pulsa 'Ejecutar predicción' para ver el resultado.")
            _render_kpi_stack(evaluation)

        with st.container(border=True, key="prediction-results-card"):
            _render_results_socialization(evaluation)
            if prediction_cache:
                _html(
                    f"""
                    <div class="bankify-result-card">
                        <h3>Explicación pedagógica</h3>
                        <p>{prediction_cache['pedagogical_summary']}</p>
                    </div>
                    """
                )

        if prediction_cache:
            progress = self._exercise_progress(record, bundle.exercise)
            _html(
                """
                <div class="bankify-question-box">
                    <span class="bankify-question-box-tag">Tu turno · Reflexión</span>
                    <p>¿Qué entendiste de la explicación del modelo y qué variable te parece más determinante?</p>
                </div>
                """
            )
            with st.form("prediction_reflection_form"):
                reflection = st.text_area(
                    "¿Qué entendiste de la explicación del modelo?",
                    value=progress.prediction_reflection if progress else "",
                    height=120,
                )
                submitted = st.form_submit_button("Guardar comprensión", type="primary", use_container_width=True)
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
            with st.spinner("Preparando visualización 3D de comentarios..."):
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
            "analytics_comment_panorama": "#34d399",
            "analytics_comment_cada_dato": "#14b8a6",
            "analytics_comment_relaciones": "#0d9488",
            "prediction_reflection": "#f59e0b",
        }
        symbol_map = {
            "dataset_comment": "circle",
            "analytics_comment_panorama": "square",
            "analytics_comment_cada_dato": "diamond",
            "analytics_comment_relaciones": "cross",
            "prediction_reflection": "x",
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

    def _render_final_feedback(self) -> None:
        record = self._current_record()
        bundle = self._current_bundle()
        if not record or bundle is None:
            return
        st.title("Retroalimentación final")
        st.write("Ejercicio creado por los monitores de Ingeniería Estadística.")
        progress = self._exercise_progress(record, bundle.exercise)
        previous = progress.feedback if progress else None
        default_star_index = max(0, min(4, previous.rating - 1)) if previous else 3
        st.write("Califica la experiencia")
        selected_star = st.feedback("stars", default=default_star_index, key="feedback_stars")
        rating = (selected_star if selected_star is not None else default_star_index) + 1
        with st.form("feedback_form"):
            summary = st.text_area("Resumen de la experiencia", value=previous.summary if previous else "")
            missing_topics = ""
            improvement_ideas = ""
            if rating <= 3:
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
