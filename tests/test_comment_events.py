from __future__ import annotations

from domain.models import ExerciseProgress
from services.comment_events import build_comment_event_records, build_comment_hash


def test_build_comment_event_records_creates_one_event_per_valid_comment() -> None:
    progress = ExerciseProgress(
        exercise="credit_approval",
        dataset_comment="El dataset sugiere ingresos altos con deuda contenida.",
        analytics_comment="Los gráficos muestran menos riesgo cuando mejora la relación cuota-ingreso.",
        prediction_reflection="La explicación del modelo confirmó esa tendencia.",
        updated_at="2026-04-03T10:00:00+00:00",
    )

    events = build_comment_event_records(
        participant_id="p-001",
        public_alias="P-001",
        exercise="credit_approval",
        progress=progress,
    )

    assert len(events) == 3
    assert [event.comment_type for event in events] == [
        "dataset_comment",
        "analytics_comment",
        "prediction_reflection",
    ]
    assert all(event.participant_id == "p-001" for event in events)
    assert all(event.public_alias == "P-001" for event in events)
    assert all(event.updated_at == "2026-04-03T10:00:00+00:00" for event in events)
    assert all(event.data_origin == "app_runtime" for event in events)


def test_build_comment_event_records_skips_non_meaningful_comments() -> None:
    progress = ExerciseProgress(
        exercise="credit_approval",
        dataset_comment="ok",
        analytics_comment="N/A",
        prediction_reflection="La predicción sí fue útil para contrastar variables.",
    )

    events = build_comment_event_records(
        participant_id="p-001",
        public_alias="P-001",
        exercise="credit_approval",
        progress=progress,
    )

    assert len(events) == 1
    assert events[0].comment_type == "prediction_reflection"


def test_build_comment_hash_matches_clean_comment_payload() -> None:
    raw_text = "¡La relación ingreso/cuota fue MUY clara!"
    clean_hash = build_comment_hash("relacion ingreso cuota clara", is_clean=True)

    assert build_comment_hash(raw_text) == clean_hash


def test_build_comment_event_records_keep_stable_logical_key_when_comment_text_changes() -> None:
    first_progress = ExerciseProgress(
        exercise="credit_approval",
        dataset_comment="El dataset sugiere ingresos altos con deuda contenida.",
        updated_at="2026-04-03T10:00:00+00:00",
    )
    edited_progress = ExerciseProgress(
        exercise="credit_approval",
        dataset_comment="El dataset sugiere ingresos estables y menor presión de deuda.",
        updated_at="2026-04-03T10:05:00+00:00",
    )

    first_event = build_comment_event_records(
        participant_id="p-001",
        public_alias="P-001",
        exercise="credit_approval",
        progress=first_progress,
    )[0]
    edited_event = build_comment_event_records(
        participant_id="p-001",
        public_alias="P-001",
        exercise="credit_approval",
        progress=edited_progress,
    )[0]

    assert first_event.logical_key() == edited_event.logical_key() == (
        "p-001",
        "credit_approval",
        "dataset_comment",
    )
    assert first_event.comment_hash != edited_event.comment_hash
    assert edited_event.comment_text.endswith("presión de deuda.")
