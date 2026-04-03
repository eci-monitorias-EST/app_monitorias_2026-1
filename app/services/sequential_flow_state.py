from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Sequence

from domain.models import ExerciseProgress, ParticipantRecord


MeaningfulTextChecker = Callable[[str], bool]
StepGuard = Callable[["FlowContext"], bool]


@dataclass(frozen=True)
class FlowContext:
    record: ParticipantRecord | None
    has_meaningful_text: MeaningfulTextChecker

    @property
    def selected_exercise(self) -> str | None:
        if self.record is None:
            return None
        return self.record.selected_exercise

    @property
    def progress(self) -> ExerciseProgress | None:
        if self.record is None or self.record.selected_exercise is None:
            return None
        return self.record.exercise_progress.get(self.record.selected_exercise)


@dataclass(frozen=True)
class FlowStep:
    id: int
    title: str
    renderer_name: str
    can_advance: StepGuard


class SequentialFlowStateMachine:
    def __init__(self, steps: Sequence[FlowStep]) -> None:
        if not steps:
            raise ValueError("Sequential flow requires at least one step.")
        expected_ids = list(range(1, len(steps) + 1))
        actual_ids = [step.id for step in steps]
        if actual_ids != expected_ids:
            raise ValueError("Sequential flow steps must use consecutive ids starting at 1.")
        self.steps: tuple[FlowStep, ...] = tuple(steps)

    @property
    def total_steps(self) -> int:
        return len(self.steps)

    def get_step(self, step_id: int) -> FlowStep:
        if step_id < 1 or step_id > self.total_steps:
            raise ValueError(f"Unknown sequential flow step: {step_id}")
        return self.steps[step_id - 1]

    def can_advance(self, step_id: int, context: FlowContext) -> bool:
        if step_id >= self.total_steps:
            return False
        return self.get_step(step_id).can_advance(context)

    def next_step_id(self, step_id: int, context: FlowContext) -> int | None:
        if not self.can_advance(step_id, context):
            return None
        return min(self.total_steps, step_id + 1)

    def previous_step_id(self, step_id: int) -> int:
        self.get_step(step_id)
        return max(1, step_id - 1)


def build_sequential_flow_state_machine() -> SequentialFlowStateMachine:
    return SequentialFlowStateMachine(
        steps=(
            FlowStep(1, "Bienvenida", "_render_welcome", _allow_anything),
            FlowStep(2, "Recolección de datos", "_render_data_collection", _require_record),
            FlowStep(
                3,
                "Elección del ejercicio",
                "_render_exercise_choice",
                _require_selected_exercise,
            ),
            FlowStep(
                4,
                "Conozcamos a nuestros clientes",
                "_render_dataset_view",
                _require_selected_exercise,
            ),
            FlowStep(
                5,
                "Exploración y dashboard",
                "_render_dashboard",
                _require_selected_exercise,
            ),
            FlowStep(
                6,
                "Predicción explicable",
                "_render_prediction",
                _require_prediction_output,
            ),
            FlowStep(7, "Comentarios 3D", "_render_comments_projection", _require_record),
            FlowStep(8, "Retroalimentación final", "_render_final_feedback", _deny_advance),
        )
    )


def _allow_anything(_: FlowContext) -> bool:
    return True


def _deny_advance(_: FlowContext) -> bool:
    return False


def _require_record(context: FlowContext) -> bool:
    return context.record is not None


def _require_selected_exercise(context: FlowContext) -> bool:
    return bool(context.record and context.selected_exercise)


def _require_prediction_output(context: FlowContext) -> bool:
    progress = context.progress
    if progress is None:
        return False
    return bool(progress.prediction_output)
