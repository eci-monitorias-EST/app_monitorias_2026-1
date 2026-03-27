from __future__ import annotations

from pathlib import Path

from domain.models import FeedbackRecord
from services.storage import JsonStateStore


def test_upsert_participant_is_idempotent(tmp_path: Path) -> None:
    store = JsonStateStore(path=tmp_path / "state.json")
    first = store.upsert_participant("student@uni.edu", {"name": "Ana"})
    second = store.upsert_participant("student@uni.edu", {"name": "Ana María"})

    assert first.participant_id == second.participant_id
    assert second.profile["name"] == "Ana María"


def test_progress_and_feedback_update_existing_record(tmp_path: Path) -> None:
    store = JsonStateStore(path=tmp_path / "state.json")
    participant = store.upsert_participant("user-001", {"name": "Luis"})
    store.select_exercise(participant.participant_id, "default_risk")
    store.upsert_exercise_progress(
        participant.participant_id,
        "default_risk",
        {"dataset_comment": "Primer comentario"},
    )
    updated = store.upsert_exercise_progress(
        participant.participant_id,
        "default_risk",
        {"analytics_comment": "Hallazgo actualizado"},
    )
    feedback = FeedbackRecord(rating=5, summary="Muy útil")
    completed = store.upsert_feedback(participant.participant_id, feedback)
    completed = store.mark_completed(participant.participant_id)

    progress = updated.exercise_progress["default_risk"]
    assert progress.dataset_comment == "Primer comentario"
    assert progress.analytics_comment == "Hallazgo actualizado"
    assert completed.feedback is not None
    assert completed.completed_at is not None
