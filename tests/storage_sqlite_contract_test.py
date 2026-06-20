from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Protocol

import pytest

from domain.models import CompletedComment, FeedbackRecord, ParticipantRecord
from services.comment_events import build_comment_hash
from services.storage_sqlite import EmbeddingCacheRow, ProjectionCacheRow


class SQLiteStateStoreContract(Protocol):
    def create_participant(self, profile: dict[str, Any]) -> ParticipantRecord: ...

    def upsert_participant(
        self, access_key: str, profile: dict[str, Any]
    ) -> ParticipantRecord: ...

    def update_profile(
        self, participant_id: str, profile: dict[str, Any]
    ) -> ParticipantRecord: ...

    def get_participant(self, access_code: str) -> ParticipantRecord | None: ...

    def get_participant_by_id(
        self, participant_id: str
    ) -> ParticipantRecord | None: ...

    def select_exercise(
        self, participant_id: str, exercise: str
    ) -> ParticipantRecord: ...

    def upsert_exercise_progress(
        self, participant_id: str, exercise: str, payload: dict[str, Any]
    ) -> ParticipantRecord: ...

    def upsert_feedback(
        self, participant_id: str, exercise: str, feedback: FeedbackRecord
    ) -> ParticipantRecord: ...

    def mark_completed(
        self, participant_id: str, exercise: str
    ) -> ParticipantRecord: ...

    def list_completed_comments(
        self, exercise: str, current_participant_id: str
    ) -> list[CompletedComment]: ...

    def upsert_embeddings_cache(self, rows: list[EmbeddingCacheRow]) -> None: ...

    def query_embeddings_cache(
        self, *, exercise: str, embedding_version: str, comment_hashes: list[str]
    ) -> list[EmbeddingCacheRow]: ...

    def upsert_projection_cache(self, rows: list[ProjectionCacheRow]) -> None: ...

    def query_projection_cache(
        self, *, exercise: str, projection_version: str, comment_hashes: list[str]
    ) -> list[ProjectionCacheRow]: ...


@pytest.fixture()
def store(tmp_path: Path) -> SQLiteStateStoreContract:
    try:
        from services.storage_sqlite import SQLiteStateStore
    except ModuleNotFoundError as exc:
        if exc.name != "services.storage_sqlite":
            raise
        pytest.fail(f"SQLiteStateStore is not implemented yet: {exc}")

    return SQLiteStateStore(db_path=tmp_path / "state.db")


def test_participant_profile_round_trip(store: SQLiteStateStoreContract) -> None:
    first = store.upsert_participant(
        "student@uni.edu",
        {"name": "Ana", "age": 19, "grade": "11"},
    )
    updated = store.update_profile(
        first.participant_id,
        {"name": "Ana María", "program": "Ciencias"},
    )
    recovered = store.get_participant("student@uni.edu")
    recovered_by_id = store.get_participant_by_id(first.participant_id)

    assert updated.participant_id == first.participant_id
    assert recovered is not None
    assert recovered_by_id is not None
    assert recovered.profile == {
        "name": "Ana María",
        "age": 19,
        "grade": "11",
        "program": "Ciencias",
    }
    assert recovered_by_id.profile == recovered.profile


def test_create_participant_generates_access_code_and_alias(
    store: SQLiteStateStoreContract,
) -> None:
    first = store.create_participant({"name": "Ana"})
    second = store.create_participant({"name": "Luis"})

    assert first.public_alias == "P-001"
    assert second.public_alias == "P-002"
    assert first.access_code_display
    assert second.access_code_display
    assert first.access_code_hash != second.access_code_hash
    assert store.get_participant(first.access_code_display) is not None


def test_selected_exercise_round_trip(store: SQLiteStateStoreContract) -> None:
    participant = store.upsert_participant("student-selected", {"name": "Luis"})

    store.select_exercise(participant.participant_id, "credit_approval")
    recovered = store.get_participant_by_id(participant.participant_id)

    assert recovered is not None
    assert recovered.selected_exercise == "credit_approval"


def test_progress_with_prediction_inputs_and_output_round_trip(
    store: SQLiteStateStoreContract,
) -> None:
    participant = store.upsert_participant("student-progress", {"name": "Mora"})

    store.upsert_exercise_progress(
        participant.participant_id,
        "default_risk",
        {
            "dataset_comment": "El dataset concentra mora alta en pagos atrasados.",
            "analytics_comment": (
                "La visualización separa claramente deuda y antigüedad."
            ),
            "prediction_reflection": (
                "La predicción final coincide con el análisis previo."
            ),
            "prediction_inputs": {"age": 41, "late_payments": 3},
            "prediction_output": {"label": "Mora alta", "probability": 0.87},
        },
    )
    recovered = store.get_participant_by_id(participant.participant_id)

    assert recovered is not None
    progress = recovered.exercise_progress["default_risk"]
    assert progress.dataset_comment.startswith("El dataset")
    assert progress.prediction_inputs == {"age": 41, "late_payments": 3}
    assert progress.prediction_output == {"label": "Mora alta", "probability": 0.87}


def test_feedback_and_completion_round_trip(store: SQLiteStateStoreContract) -> None:
    participant = store.upsert_participant("student-feedback", {"name": "Eva"})
    feedback = FeedbackRecord(
        rating=5,
        summary="Muy útil",
        missing_topics="Más ejemplos",
        improvement_ideas="Agregar comparación",
    )

    store.upsert_feedback(participant.participant_id, "credit_approval", feedback)
    completed = store.mark_completed(participant.participant_id, "credit_approval")

    progress = completed.exercise_progress["credit_approval"]
    assert progress.feedback is not None
    assert progress.feedback.summary == "Muy útil"
    assert progress.feedback.missing_topics == "Más ejemplos"
    assert progress.completed_at is not None


def test_list_completed_comments_matches_json_store_parity_rules(
    store: SQLiteStateStoreContract,
) -> None:
    current = store.upsert_participant("current-user", {"name": "Ada"})
    peer = store.upsert_participant("peer-user", {"name": "Paz"})
    no_prediction = store.upsert_participant("without-prediction", {"name": "Noa"})
    noisy = store.upsert_participant("noisy-user", {"name": "Teo"})
    other_exercise = store.upsert_participant("other-exercise", {"name": "Ivo"})

    store.upsert_exercise_progress(
        current.participant_id,
        "credit_approval",
        {
            "dataset_comment": "Detecté ingresos estables combinados con deuda baja.",
            "analytics_comment": (
                "El análisis muestra menor riesgo con cuota controlada."
            ),
            "prediction_reflection": (
                "La predicción aprobada coincide con esas señales."
            ),
            "prediction_output": {"label": "Aprobado", "probability": 0.81},
        },
    )
    store.upsert_exercise_progress(
        peer.participant_id,
        "credit_approval",
        {
            "dataset_comment": (
                "El historial de pagos sostiene la aprobación de crédito."
            ),
            "prediction_output": {"label": "Aprobado", "probability": 0.72},
        },
    )
    store.upsert_exercise_progress(
        no_prediction.participant_id,
        "credit_approval",
        {"dataset_comment": "Comentario suficientemente largo pero sin predicción."},
    )
    store.upsert_exercise_progress(
        noisy.participant_id,
        "credit_approval",
        {
            "dataset_comment": "ok",
            "analytics_comment": "N/A",
            "prediction_reflection": "hola",
            "prediction_output": {"label": "Aprobado", "probability": 0.61},
        },
    )
    store.upsert_exercise_progress(
        other_exercise.participant_id,
        "default_risk",
        {
            "dataset_comment": "Este comentario pertenece a otro ejercicio.",
            "prediction_output": {"label": "Mora alta", "probability": 0.9},
        },
    )

    comments = store.list_completed_comments("credit_approval", current.participant_id)

    assert len(comments) == 4
    assert {comment.participant_id for comment in comments} == {
        current.participant_id,
        peer.participant_id,
    }
    assert [
        comment.current_user
        for comment in comments
        if comment.participant_id == current.participant_id
    ] == [True, True, True]
    assert [
        comment.current_user
        for comment in comments
        if comment.participant_id == peer.participant_id
    ] == [False]
    assert {comment.exercise for comment in comments} == {"credit_approval"}
    assert {comment.comment_type for comment in comments} == {
        "dataset_comment",
        "analytics_comment_panorama",
        "prediction_reflection",
    }


def test_cache_upsert_query_preserves_duplicate_hash_metadata(
    store: SQLiteStateStoreContract,
) -> None:
    shared_hash = build_comment_hash("ingreso estable deuda baja")
    embedding_rows: list[EmbeddingCacheRow] = [
        {
            "participant_id": "p-001",
            "exercise": "credit_approval",
            "comment_hash": shared_hash,
            "embedding_version": "emb-v1",
            "embedding_provider": "sentence_transformers_minilm",
            "comment_type": "dataset_comment",
            "comment_text": "Ingreso estable y deuda baja",
            "clean_comment": "ingreso estable deuda baja",
            "embedding_vector_json": "[0.1, 0.2, 0.3]",
        },
        {
            "participant_id": "p-002",
            "exercise": "credit_approval",
            "comment_hash": shared_hash,
            "embedding_version": "emb-v1",
            "embedding_provider": "sentence_transformers_minilm",
            "comment_type": "analytics_comment",
            "comment_text": "Ingreso estable y deuda baja",
            "embedding_vector_json": "[0.4, 0.5, 0.6]",
        },
    ]
    projection_rows: list[ProjectionCacheRow] = [
        {
            "participant_id": row["participant_id"],
            "public_alias": f"P-00{index}",
            "exercise": row["exercise"],
            "comment_hash": row["comment_hash"],
            "projection_version": "proj-v1",
            "embedding_provider": row["embedding_provider"],
            "reduction_provider": "umap",
            "comment_type": row["comment_type"],
            "comment_text": row["comment_text"],
            "clean_comment": row.get("clean_comment", ""),
            "x": float(index),
            "y": float(index + 1),
            "z": float(index + 2),
        }
        for index, row in enumerate(embedding_rows, start=1)
    ]

    store.upsert_embeddings_cache(embedding_rows)
    store.upsert_projection_cache(projection_rows)
    embeddings = store.query_embeddings_cache(
        exercise="credit_approval",
        embedding_version="emb-v1",
        comment_hashes=[shared_hash],
    )
    projections = store.query_projection_cache(
        exercise="credit_approval",
        projection_version="proj-v1",
        comment_hashes=[shared_hash],
    )

    assert {(row["participant_id"], row["comment_type"]) for row in embeddings} == {
        ("p-001", "dataset_comment"),
        ("p-002", "analytics_comment"),
    }
    assert {(row["participant_id"], row["comment_type"]) for row in projections} == {
        ("p-001", "dataset_comment"),
        ("p-002", "analytics_comment"),
    }
    assert {row["comment_hash"] for row in embeddings + projections} == {shared_hash}


def test_invalid_json_payloads_fall_back_to_safe_empty_values(
    tmp_path: Path,
) -> None:
    from services.storage_sqlite import SQLiteStateStore

    db_path = tmp_path / "state.db"
    store = SQLiteStateStore(db_path=db_path)
    participant = store.upsert_participant("invalid-json", {"name": "Iris"})

    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "UPDATE perfil_participante SET profile_json = ? WHERE participant_id = ?",
            ("{invalid", participant.participant_id),
        )
        conn.execute(
            """
            INSERT INTO respuesta(
                participant_id,
                exercise,
                prediction_inputs,
                prediction_output
            )
            VALUES (?, ?, ?, ?)
            """,
            (participant.participant_id, "credit_approval", "{bad", "[1]"),
        )

    recovered = store.get_participant_by_id(participant.participant_id)

    assert recovered is not None
    assert recovered.profile == {}
    progress = recovered.exercise_progress["credit_approval"]
    assert progress.prediction_inputs == {}
    assert progress.prediction_output == {}
