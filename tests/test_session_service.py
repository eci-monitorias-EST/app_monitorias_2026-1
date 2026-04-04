from __future__ import annotations

from pathlib import Path
from typing import Any

from services.remote_sync import RemoteSyncClient
from services.session_service import SessionService
from services.storage import JsonStateStore


class RecordingRemoteSyncClient(RemoteSyncClient):
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def sync_participant(self, participant_payload: dict[str, Any]) -> None:
        self.calls.append(("participant", participant_payload))

    def sync_progress(self, progress_payload: dict[str, Any]) -> None:
        self.calls.append(("progress", progress_payload))

    def sync_feedback(self, feedback_payload: dict[str, Any]) -> None:
        self.calls.append(("feedback", feedback_payload))

    def sync_comment_events(self, comment_events_payload: dict[str, Any]) -> None:
        self.calls.append(("comment_events", comment_events_payload))

    def sync_completion(self, completion_payload: dict[str, Any]) -> None:
        self.calls.append(("completion", completion_payload))


def test_start_session_persists_local_record_and_syncs_expected_payload(tmp_path: Path) -> None:
    remote_sync = RecordingRemoteSyncClient()
    service = SessionService(
        store=JsonStateStore(path=tmp_path / "state.json"),
        remote_sync=remote_sync,
    )

    record = service.start_session({"name": "Ana", "course": "ML"})
    persisted = service.recover(record.access_code_display)

    assert persisted is not None
    assert persisted.participant_id == record.participant_id
    assert persisted.profile == {"name": "Ana", "course": "ML"}
    assert persisted.access_code_display == record.access_code_display
    assert remote_sync.calls == [
        (
            "participant",
            {
                "participant_id": record.participant_id,
                "public_alias": record.public_alias,
                "access_code_display": record.access_code_display,
                "access_code_hash": record.access_code_hash,
                "profile": {"name": "Ana", "course": "ML"},
            },
        )
    ]


def test_login_or_resume_recovers_existing_record_by_access_code(tmp_path: Path) -> None:
    remote_sync = RecordingRemoteSyncClient()
    service = SessionService(
        store=JsonStateStore(path=tmp_path / "state.json"),
        remote_sync=remote_sync,
    )

    created = service.start_session({"name": "Ana"})

    resumed = service.login_or_resume(created.access_code_display, {"course": "ML"})

    assert resumed.participant_id == created.participant_id
    assert resumed.profile == {"name": "Ana", "course": "ML"}
    assert resumed.access_code_display == created.access_code_display


def test_save_feedback_updates_store_and_syncs_serialized_feedback_payload(tmp_path: Path) -> None:
    remote_sync = RecordingRemoteSyncClient()
    store = JsonStateStore(path=tmp_path / "state.json")
    service = SessionService(store=store, remote_sync=remote_sync)
    participant = service.start_session({"name": "Luis"})

    updated = service.save_feedback(
        participant.participant_id,
        "default_risk",
        {
            "rating": "5",
            "summary": "Muy útil",
            "missing_topics": "Curvas ROC",
            "improvement_ideas": "Más ejemplos",
        },
    )

    progress = updated.exercise_progress["default_risk"]

    assert progress.feedback is not None
    assert progress.feedback.rating == 5
    assert progress.feedback.summary == "Muy útil"
    assert progress.feedback.missing_topics == "Curvas ROC"
    assert progress.feedback.improvement_ideas == "Más ejemplos"

    feedback_call = remote_sync.calls[-1]
    assert feedback_call[0] == "feedback"
    assert feedback_call[1]["participant_id"] == participant.participant_id
    assert feedback_call[1]["exercise"] == "default_risk"
    assert feedback_call[1]["payload"] == {
        "rating": 5,
        "summary": "Muy útil",
        "missing_topics": "Curvas ROC",
        "improvement_ideas": "Más ejemplos",
        "updated_at": progress.feedback.updated_at,
    }


def test_save_progress_syncs_consolidated_exercise_payload_instead_of_partial_payload(
    tmp_path: Path,
) -> None:
    remote_sync = RecordingRemoteSyncClient()
    store = JsonStateStore(path=tmp_path / "state.json")
    service = SessionService(store=store, remote_sync=remote_sync)
    participant = service.start_session({"name": "Mica"})

    service.save_progress(
        participant.participant_id,
        "credit_approval",
        {"dataset_comment": "Primero entendí el dataset."},
    )
    updated = service.save_progress(
        participant.participant_id,
        "credit_approval",
        {"analytics_comment": "Después interpreté los gráficos."},
    )

    progress = updated.exercise_progress["credit_approval"]
    progress_call = next(call for call in reversed(remote_sync.calls) if call[0] == "progress")

    assert progress.dataset_comment == "Primero entendí el dataset."
    assert progress.analytics_comment == "Después interpreté los gráficos."
    assert progress_call == (
        "progress",
        {
            "participant_id": participant.participant_id,
            "exercise": "credit_approval",
            "payload": {
                "dataset_comment": "Primero entendí el dataset.",
                "analytics_comment": "Después interpreté los gráficos.",
                "prediction_reflection": "",
                "prediction_inputs": {},
                "prediction_output": {},
            },
        },
    )


def test_save_progress_syncs_individual_comment_events_with_hashes(tmp_path: Path) -> None:
    remote_sync = RecordingRemoteSyncClient()
    store = JsonStateStore(path=tmp_path / "state.json")
    service = SessionService(store=store, remote_sync=remote_sync)
    participant = service.start_session({"name": "Noa"})

    service.save_progress(
        participant.participant_id,
        "credit_approval",
        {
            "dataset_comment": "El dataset muestra ingresos más estables que la deuda.",
            "analytics_comment": "Los gráficos refuerzan esa separación entre grupos.",
        },
    )

    comment_event_call = next(call for call in reversed(remote_sync.calls) if call[0] == "comment_events")

    assert comment_event_call[1]["participant_id"] == participant.participant_id
    assert comment_event_call[1]["exercise"] == "credit_approval"
    assert len(comment_event_call[1]["rows"]) == 2
    assert {row["comment_type"] for row in comment_event_call[1]["rows"]} == {
        "dataset_comment",
        "analytics_comment",
    }
    assert all(len(row["comment_hash"]) == 64 for row in comment_event_call[1]["rows"])


def test_multi_exercise_progress_and_feedback_stay_bounded_to_two_records_per_participant(tmp_path: Path) -> None:
    remote_sync = RecordingRemoteSyncClient()
    store = JsonStateStore(path=tmp_path / "state.json")
    service = SessionService(store=store, remote_sync=remote_sync)
    participant = service.start_session({"name": "Luna"})

    for exercise in ("credit_approval", "default_risk"):
        service.save_progress(
            participant.participant_id,
            exercise,
            {
                "dataset_comment": f"Comentario inicial para {exercise} con suficiente detalle.",
                "analytics_comment": f"Hallazgo analítico para {exercise} con suficiente contexto.",
                "prediction_reflection": f"Reflexión del modelo para {exercise} con suficiente contexto.",
                "prediction_output": {"label": "ok", "probability": 0.75},
            },
        )
        service.save_feedback(
            participant.participant_id,
            exercise,
            {
                "rating": 4,
                "summary": f"Resumen final para {exercise} con suficiente detalle.",
            },
        )

    service.save_progress(
        participant.participant_id,
        "credit_approval",
        {"analytics_comment": "Hallazgo editado para credit_approval con suficiente contexto adicional."},
    )
    service.save_feedback(
        participant.participant_id,
        "default_risk",
        {
            "rating": 5,
            "summary": "Resumen editado para default_risk con suficiente detalle adicional.",
        },
    )

    persisted = service.get_record(participant.participant_id)

    assert persisted is not None
    assert set(persisted.exercise_progress) == {"credit_approval", "default_risk"}
    assert len(persisted.exercise_progress) == 2
    assert sum(1 for progress in persisted.exercise_progress.values() if progress.feedback is not None) == 2


def test_editing_same_comment_type_updates_same_logical_comment_event_row(tmp_path: Path) -> None:
    remote_sync = RecordingRemoteSyncClient()
    store = JsonStateStore(path=tmp_path / "state.json")
    service = SessionService(store=store, remote_sync=remote_sync)
    participant = service.start_session({"name": "Sofi"})

    service.save_progress(
        participant.participant_id,
        "credit_approval",
        {"dataset_comment": "Comentario inicial sobre el dataset con suficiente detalle."},
    )
    service.save_progress(
        participant.participant_id,
        "credit_approval",
        {"dataset_comment": "Comentario editado sobre el dataset con suficiente detalle y contexto."},
    )

    comment_event_calls = [call for call in remote_sync.calls if call[0] == "comment_events"]

    assert len(comment_event_calls) == 2
    first_row = comment_event_calls[0][1]["rows"][0]
    second_row = comment_event_calls[1][1]["rows"][0]
    assert (first_row["participant_id"], first_row["exercise"], first_row["comment_type"]) == (
        second_row["participant_id"],
        second_row["exercise"],
        second_row["comment_type"],
    )
    assert first_row["comment_hash"] != second_row["comment_hash"]
    assert second_row["comment_text"].startswith("Comentario editado")


def test_session_and_completion_events_define_at_most_three_control_rows(tmp_path: Path) -> None:
    remote_sync = RecordingRemoteSyncClient()
    store = JsonStateStore(path=tmp_path / "state.json")
    service = SessionService(store=store, remote_sync=remote_sync)
    participant = service.start_session({"name": "Teo"})

    service.complete_activity(participant.participant_id, "credit_approval")
    service.complete_activity(participant.participant_id, "default_risk")
    service.complete_activity(participant.participant_id, "credit_approval")

    control_keys = {
        (payload["participant_id"], "session")
        for call_type, payload in remote_sync.calls
        if call_type == "participant"
    }
    control_keys.update(
        (payload["participant_id"], payload["exercise"])
        for call_type, payload in remote_sync.calls
        if call_type == "completion"
    )

    assert control_keys == {
        (participant.participant_id, "session"),
        (participant.participant_id, "credit_approval"),
        (participant.participant_id, "default_risk"),
    }
