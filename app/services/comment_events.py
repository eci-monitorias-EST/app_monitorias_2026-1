from __future__ import annotations

import hashlib
import re
import unicodedata
from typing import Any, Iterable, Mapping

from domain.models import CommentEvent, ExerciseProgress
from services.dashboard_sections import SECTION_LABELS, split_sections
from services.submission_validation import SubmissionValidationService


# El dashboard exploratorio (app/pages/eda_dashboard.py) tiene 3 preguntas
# (una por capítulo) combinadas en ExerciseProgress.analytics_comment. Para que
# la visualización 3D muestre un punto por pregunta respondida (en vez de un
# solo punto para las 3 combinadas), cada capítulo tiene su propio comment_type.
ANALYTICS_SECTION_COMMENT_TYPES: dict[int, str] = {
    1: "analytics_comment_panorama",
    2: "analytics_comment_cada_dato",
    3: "analytics_comment_relaciones",
}

COMMENT_TYPE_LABELS: dict[str, str] = {
    "dataset_comment": "Dataset",
    **{
        comment_type: f"Hallazgo · {SECTION_LABELS[chapter]}"
        for chapter, comment_type in ANALYTICS_SECTION_COMMENT_TYPES.items()
    },
    "prediction_reflection": "Reflexión del modelo",
}

SPANISH_STOPWORDS = {
    "de", "la", "el", "los", "las", "que", "y", "o", "en", "un", "una", "para", "por",
    "con", "del", "al", "se", "su", "sus", "me", "mi", "mis", "es", "son", "muy", "mas",
    "pero", "porque", "como", "lo", "le", "les", "ha", "han", "fue", "ser", "estar",
}


class CommentTextCleaner:
    def clean(self, text: str) -> str:
        normalized = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
        normalized = normalized.lower()
        normalized = re.sub(r"https?://\S+|www\.\S+", " ", normalized)
        normalized = re.sub(r"[^a-z0-9\s]", " ", normalized)
        normalized = re.sub(r"\s+", " ", normalized).strip()
        tokens = [token for token in normalized.split() if token not in SPANISH_STOPWORDS]
        return " ".join(tokens)


def build_comment_hash(comment: str, *, is_clean: bool = False, cleaner: CommentTextCleaner | None = None) -> str:
    normalized = comment.strip() if is_clean else (cleaner or CommentTextCleaner()).clean(comment)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def iter_comment_fields(progress: ExerciseProgress) -> Iterable[tuple[str, str]]:
    yield "dataset_comment", str(progress.dataset_comment or "").strip()
    sections = split_sections(progress.analytics_comment)
    for chapter, comment_type in ANALYTICS_SECTION_COMMENT_TYPES.items():
        yield comment_type, sections[chapter].strip()
    yield "prediction_reflection", str(progress.prediction_reflection or "").strip()


def build_comment_event_records(
    *,
    participant_id: str,
    public_alias: str,
    exercise: str,
    progress: ExerciseProgress,
    validator: SubmissionValidationService | None = None,
    cleaner: CommentTextCleaner | None = None,
    is_test_data: bool = False,
    test_batch_id: str = "",
    data_origin: str = "app_runtime",
) -> list[CommentEvent]:
    validation_service = validator or SubmissionValidationService()
    text_cleaner = cleaner or CommentTextCleaner()
    events: list[CommentEvent] = []
    for comment_type, comment_text in iter_comment_fields(progress):
        if not comment_text:
            continue
        if not validation_service.has_meaningful_learning_text(comment_text):
            continue
        clean_comment = text_cleaner.clean(comment_text)
        events.append(
            CommentEvent(
                participant_id=participant_id,
                public_alias=public_alias,
                exercise=exercise,
                comment_type=comment_type,
                comment_text=comment_text,
                clean_comment=clean_comment,
                comment_hash=build_comment_hash(clean_comment, is_clean=True),
                updated_at=progress.updated_at,
                is_test_data=is_test_data,
                test_batch_id=test_batch_id,
                data_origin=data_origin,
            )
        )
    return events


def build_comment_event_rows(
    *,
    participant_id: str,
    public_alias: str,
    exercise: str,
    progress: ExerciseProgress,
    validator: SubmissionValidationService | None = None,
    cleaner: CommentTextCleaner | None = None,
    is_test_data: bool = False,
    test_batch_id: str = "",
    data_origin: str = "app_runtime",
) -> list[dict[str, Any]]:
    return [
        event.to_dict()
        for event in build_comment_event_records(
            participant_id=participant_id,
            public_alias=public_alias,
            exercise=exercise,
            progress=progress,
            validator=validator,
            cleaner=cleaner,
            is_test_data=is_test_data,
            test_batch_id=test_batch_id,
            data_origin=data_origin,
        )
    ]


def build_comment_event_rows_from_payload(
    *,
    participant_id: str,
    public_alias: str,
    exercise: str,
    progress_payload: Mapping[str, Any],
    validator: SubmissionValidationService | None = None,
    cleaner: CommentTextCleaner | None = None,
    is_test_data: bool = False,
    test_batch_id: str = "",
    data_origin: str = "app_runtime",
    updated_at: str = "",
) -> list[dict[str, Any]]:
    progress = ExerciseProgress(
        exercise=exercise,
        dataset_comment=str(progress_payload.get("dataset_comment", "")).strip(),
        analytics_comment=str(progress_payload.get("analytics_comment", "")).strip(),
        prediction_reflection=str(progress_payload.get("prediction_reflection", "")).strip(),
        prediction_inputs=dict(progress_payload.get("prediction_inputs", {})),
        prediction_output=dict(progress_payload.get("prediction_output", {})),
        updated_at=updated_at or ExerciseProgress(exercise=exercise).updated_at,
    )
    return build_comment_event_rows(
        participant_id=participant_id,
        public_alias=public_alias,
        exercise=exercise,
        progress=progress,
        validator=validator,
        cleaner=cleaner,
        is_test_data=is_test_data,
        test_batch_id=test_batch_id,
        data_origin=data_origin,
    )
