from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class ExerciseOption:
    CREDIT_APPROVAL = "credit_approval"
    DEFAULT_RISK = "default_risk"

    LABELS = {
        CREDIT_APPROVAL: "Aprobación de crédito",
        DEFAULT_RISK: "Probabilidad de mora",
    }


@dataclass
class VariableDescriptor:
    key: str
    label: str
    description: str
    variable_type: str
    source: str
    official_name: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ExerciseProgress:
    exercise: str
    dataset_comment: str = ""
    analytics_comment: str = ""
    prediction_reflection: str = ""
    prediction_inputs: dict[str, Any] = field(default_factory=dict)
    prediction_output: dict[str, Any] = field(default_factory=dict)
    updated_at: str = field(default_factory=utc_now_iso)

    def merge(self, payload: dict[str, Any]) -> None:
        for key, value in payload.items():
            if value is not None:
                setattr(self, key, value)
        self.updated_at = utc_now_iso()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class FeedbackRecord:
    rating: int
    summary: str
    missing_topics: str = ""
    improvement_ideas: str = ""
    updated_at: str = field(default_factory=utc_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ParticipantRecord:
    participant_id: str
    access_key_hash: str
    public_alias: str
    profile: dict[str, Any]
    selected_exercise: str | None = None
    exercise_progress: dict[str, ExerciseProgress] = field(default_factory=dict)
    feedback: FeedbackRecord | None = None
    completed_at: str | None = None
    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)

    def upsert_progress(self, exercise: str, payload: dict[str, Any]) -> ExerciseProgress:
        progress = self.exercise_progress.get(exercise)
        if progress is None:
            progress = ExerciseProgress(exercise=exercise)
            self.exercise_progress[exercise] = progress
        progress.merge(payload)
        self.updated_at = utc_now_iso()
        return progress

    def set_feedback(self, feedback: FeedbackRecord) -> None:
        self.feedback = feedback
        self.updated_at = utc_now_iso()

    def mark_completed(self) -> None:
        self.completed_at = utc_now_iso()
        self.updated_at = self.completed_at

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["exercise_progress"] = {
            key: value.to_dict() for key, value in self.exercise_progress.items()
        }
        if self.feedback is not None:
            payload["feedback"] = self.feedback.to_dict()
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ParticipantRecord":
        progress = {
            key: ExerciseProgress(**value)
            for key, value in payload.get("exercise_progress", {}).items()
        }
        feedback_payload = payload.get("feedback")
        feedback = FeedbackRecord(**feedback_payload) if feedback_payload else None
        return cls(
            participant_id=payload["participant_id"],
            access_key_hash=payload["access_key_hash"],
            public_alias=payload["public_alias"],
            profile=payload.get("profile", {}),
            selected_exercise=payload.get("selected_exercise"),
            exercise_progress=progress,
            feedback=feedback,
            completed_at=payload.get("completed_at"),
            created_at=payload.get("created_at", utc_now_iso()),
            updated_at=payload.get("updated_at", utc_now_iso()),
        )


@dataclass
class CompletedComment:
    participant_id: str
    public_alias: str
    exercise: str
    combined_comment: str
    current_user: bool = False


@dataclass
class PredictionResult:
    exercise: str
    probability: float
    label: str
    features: dict[str, Any]
    provider: str
    local_explanations: dict[str, Any]
    global_explanations: dict[str, Any]
    pedagogical_summary: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
