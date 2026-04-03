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


def test_list_completed_comments_includes_predicted_meaningful_comments_without_completion(
    tmp_path: Path,
) -> None:
    store = JsonStateStore(path=tmp_path / "state.json")
    participant = store.upsert_participant("user-3d", {"name": "Ada"})
    store.select_exercise(participant.participant_id, "credit_approval")
    store.upsert_exercise_progress(
        participant.participant_id,
        "credit_approval",
        {
            "dataset_comment": "Detecté ingresos altos combinados con cuotas bajas en varios casos.",
            "analytics_comment": "El dashboard muestra menos riesgo cuando mejora la relación ingreso-cuota.",
            "prediction_reflection": "La predicción final coincide con ese patrón observado.",
            "prediction_output": {"label": "Aprobado", "probability": 0.81},
        },
    )

    comments = store.list_completed_comments("credit_approval", participant.participant_id)

    assert len(comments) == 1
    assert comments[0].participant_id == participant.participant_id
    assert comments[0].current_user is True
    assert "Detecté ingresos altos" in comments[0].combined_comment


def test_list_completed_comments_excludes_records_without_prediction_output(tmp_path: Path) -> None:
    store = JsonStateStore(path=tmp_path / "state.json")
    participant = store.upsert_participant("user-no-prediction", {"name": "Luis"})
    store.select_exercise(participant.participant_id, "credit_approval")
    store.upsert_exercise_progress(
        participant.participant_id,
        "credit_approval",
        {
            "dataset_comment": "Analicé perfiles con deudas previas y montos elevados.",
            "analytics_comment": "Los casos de mayor mora se concentran en ingresos más bajos.",
        },
    )

    comments = store.list_completed_comments("credit_approval", participant.participant_id)

    assert comments == []


def test_list_completed_comments_excludes_non_meaningful_combined_text(tmp_path: Path) -> None:
    store = JsonStateStore(path=tmp_path / "state.json")
    participant = store.upsert_participant("user-noisy", {"name": "Noe"})
    store.select_exercise(participant.participant_id, "credit_approval")
    store.upsert_exercise_progress(
        participant.participant_id,
        "credit_approval",
        {
            "dataset_comment": "ok",
            "analytics_comment": "N/A",
            "prediction_reflection": "hola",
            "prediction_output": {"label": "Aprobado", "probability": 0.61},
        },
    )

    comments = store.list_completed_comments("credit_approval", participant.participant_id)

    assert comments == []


def test_list_completed_comments_only_uses_requested_exercise_progress(tmp_path: Path) -> None:
    store = JsonStateStore(path=tmp_path / "state.json")
    participant = store.upsert_participant("user-other-exercise", {"name": "Eva"})
    store.select_exercise(participant.participant_id, "credit_approval")
    store.upsert_exercise_progress(
        participant.participant_id,
        "default_risk",
        {
            "dataset_comment": "Encontré atrasos altos junto con cuotas vencidas frecuentes.",
            "prediction_reflection": "La predicción confirmó un riesgo de mora alto.",
            "prediction_output": {"label": "Mora alta", "probability": 0.9},
        },
    )

    comments = store.list_completed_comments("credit_approval", participant.participant_id)

    assert comments == []
