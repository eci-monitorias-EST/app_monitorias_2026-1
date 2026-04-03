from __future__ import annotations

import pytest

from domain.models import ExerciseOption, ParticipantRecord
from services.sequential_flow_state import FlowContext, build_sequential_flow_state_machine
from services.submission_validation import SubmissionValidationService


def test_next_and_previous_transitions_follow_the_declared_flow() -> None:
    machine = build_sequential_flow_state_machine()
    context = _build_context(_build_record(dataset_comment="Hallazgo suficientemente detallado sobre el dataset."))

    assert machine.previous_step_id(1) == 1
    assert machine.previous_step_id(5) == 4
    assert machine.next_step_id(1, context) == 2
    assert machine.next_step_id(8, context) is None


def test_step_two_requires_an_active_record() -> None:
    machine = build_sequential_flow_state_machine()

    assert machine.next_step_id(2, _build_context(None)) is None
    assert machine.next_step_id(2, _build_context(_build_record())) == 3


def test_step_three_requires_selected_exercise() -> None:
    machine = build_sequential_flow_state_machine()

    assert machine.next_step_id(3, _build_context(_build_record(selected_exercise=None))) is None
    assert machine.next_step_id(3, _build_context(_build_record())) == 4


@pytest.mark.parametrize(
    ("step_id", "field_name"),
    [
        (4, "dataset_comment"),
        (5, "analytics_comment"),
        (6, "prediction_reflection"),
    ],
)
def test_reflection_steps_require_meaningful_text_for_current_exercise(step_id: int, field_name: str) -> None:
    machine = build_sequential_flow_state_machine()
    blocked_record = _build_record(**{field_name: "ok"})
    allowed_record = _build_record(**{field_name: "Respuesta con contexto suficiente para validar el avance."})

    assert machine.next_step_id(step_id, _build_context(blocked_record)) is None
    assert machine.next_step_id(step_id, _build_context(allowed_record)) == step_id + 1


def test_reflection_guards_only_consider_progress_from_selected_exercise() -> None:
    machine = build_sequential_flow_state_machine()
    record = _build_record(dataset_comment="Texto corto")
    record.exercise_progress[ExerciseOption.DEFAULT_RISK].dataset_comment = (
        "Comentario largo y útil, pero pertenece a otro ejercicio y no debe habilitar el paso."
    )

    assert machine.next_step_id(4, _build_context(record)) is None


def test_invalid_step_id_raises_clear_error() -> None:
    machine = build_sequential_flow_state_machine()

    with pytest.raises(ValueError, match="Unknown sequential flow step"):
        machine.get_step(99)


def _build_context(record: ParticipantRecord | None) -> FlowContext:
    validator = SubmissionValidationService()
    return FlowContext(record=record, has_meaningful_text=validator.has_meaningful_learning_text)


def _build_record(
    *,
    selected_exercise: str | None = ExerciseOption.CREDIT_APPROVAL,
    dataset_comment: str = "",
    analytics_comment: str = "",
    prediction_reflection: str = "",
) -> ParticipantRecord:
    record = ParticipantRecord(
        participant_id="participant-1",
        access_key_hash="hash",
        public_alias="Alias 1",
        profile={"nombre": "Ada"},
        selected_exercise=selected_exercise,
    )
    record.upsert_progress(
        ExerciseOption.CREDIT_APPROVAL,
        {
            "dataset_comment": dataset_comment,
            "analytics_comment": analytics_comment,
            "prediction_reflection": prediction_reflection,
        },
    )
    record.upsert_progress(ExerciseOption.DEFAULT_RISK, {})
    return record
