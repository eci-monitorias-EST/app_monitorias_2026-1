from __future__ import annotations

import hashlib
import re
import unicodedata
from typing import Iterable

from domain.models import CommentEvent, ExerciseProgress
from services.submission_validation import SubmissionValidationService


COMMENT_TYPE_LABELS: dict[str, str] = {
    "dataset_comment": "Dataset",
    "analytics_comment": "Hallazgo analítico",
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
    for comment_type in COMMENT_TYPE_LABELS:
        yield comment_type, str(getattr(progress, comment_type, "")).strip()


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
