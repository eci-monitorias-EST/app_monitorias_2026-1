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
    store.upsert_feedback(participant.participant_id, "default_risk", feedback)
    completed = store.mark_completed(participant.participant_id, "default_risk")

    progress = completed.exercise_progress["default_risk"]
    assert progress.dataset_comment == "Primer comentario"
    assert progress.analytics_comment == "Hallazgo actualizado"
    assert progress.feedback is not None
    assert progress.completed_at is not None


def test_legacy_feedback_is_migrated_to_selected_exercise_progress(tmp_path: Path) -> None:
    store = JsonStateStore(path=tmp_path / "state.json")
    store.path.write_text(
        """
{
  "participants": {
    "legacy": {
      "participant_id": "p-001",
      "access_key_hash": "legacy",
      "public_alias": "P-001",
      "profile": {"name": "Ana"},
      "selected_exercise": "credit_approval",
      "feedback": {"rating": 4, "summary": "Muy claro", "missing_topics": "", "improvement_ideas": "", "updated_at": "2026-04-01T00:00:00+00:00"},
      "completed_at": "2026-04-01T00:10:00+00:00",
      "exercise_progress": {},
      "created_at": "2026-04-01T00:00:00+00:00",
      "updated_at": "2026-04-01T00:10:00+00:00"
    }
  },
  "metadata": {"version": 1}
}
        """.strip(),
        encoding="utf-8",
    )

    record = store.get_participant_by_id("p-001")

    assert record is not None
    progress = record.exercise_progress["credit_approval"]
    assert progress.feedback is not None
    assert progress.feedback.summary == "Muy claro"
    assert progress.completed_at == "2026-04-01T00:10:00+00:00"
