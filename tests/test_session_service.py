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

    def sync_completion(self, completion_payload: dict[str, Any]) -> None:
        self.calls.append(("completion", completion_payload))


def test_login_or_resume_persists_local_record_and_syncs_expected_payload(tmp_path: Path) -> None:
    remote_sync = RecordingRemoteSyncClient()
    service = SessionService(
        store=JsonStateStore(path=tmp_path / "state.json"),
        remote_sync=remote_sync,
    )

    record = service.login_or_resume("student-001", {"name": "Ana", "course": "ML"})
    persisted = service.recover("student-001")

    assert persisted is not None
    assert persisted.participant_id == record.participant_id
    assert persisted.profile == {"name": "Ana", "course": "ML"}
    assert remote_sync.calls == [
        (
            "participant",
            {
                "participant_id": record.participant_id,
                "public_alias": record.public_alias,
                "profile": {"name": "Ana", "course": "ML"},
            },
        )
    ]


def test_save_feedback_updates_store_and_syncs_serialized_feedback_payload(tmp_path: Path) -> None:
    remote_sync = RecordingRemoteSyncClient()
    store = JsonStateStore(path=tmp_path / "state.json")
    service = SessionService(store=store, remote_sync=remote_sync)
    participant = service.login_or_resume("student-002", {"name": "Luis"})

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
