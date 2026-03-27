from __future__ import annotations

from dataclasses import asdict

from domain.models import FeedbackRecord, ParticipantRecord
from services.remote_sync import RemoteSyncClient
from services.storage import JsonStateStore


class SessionService:
    def __init__(self, store: JsonStateStore, remote_sync: RemoteSyncClient) -> None:
        self.store = store
        self.remote_sync = remote_sync

    def login_or_resume(self, access_key: str, profile: dict[str, object]) -> ParticipantRecord:
        record = self.store.upsert_participant(access_key=access_key, profile=profile)
        self.remote_sync.sync_participant(
            {
                "participant_id": record.participant_id,
                "public_alias": record.public_alias,
                "profile": record.profile,
            }
        )
        return record

    def recover(self, access_key: str) -> ParticipantRecord | None:
        return self.store.get_participant(access_key)

    def select_exercise(self, participant_id: str, exercise: str) -> ParticipantRecord:
        record = self.store.select_exercise(participant_id, exercise)
        self.remote_sync.sync_progress(
            {
                "participant_id": participant_id,
                "exercise": exercise,
                "payload": {"selected_exercise": exercise},
            }
        )
        return record

    def save_progress(self, participant_id: str, exercise: str, payload: dict[str, object]) -> ParticipantRecord:
        record = self.store.upsert_exercise_progress(participant_id, exercise, payload)
        self.remote_sync.sync_progress(
            {"participant_id": participant_id, "exercise": exercise, "payload": payload}
        )
        return record

    def save_feedback(self, participant_id: str, payload: dict[str, object]) -> ParticipantRecord:
        feedback = FeedbackRecord(**payload)
        record = self.store.upsert_feedback(participant_id, feedback)
        self.remote_sync.sync_feedback({"participant_id": participant_id, "payload": asdict(feedback)})
        return record

    def complete_activity(self, participant_id: str) -> ParticipantRecord:
        record = self.store.mark_completed(participant_id)
        self.remote_sync.sync_completion({"participant_id": participant_id})
        return record

    def get_record(self, participant_id: str) -> ParticipantRecord | None:
        return self.store.get_participant_by_id(participant_id)
