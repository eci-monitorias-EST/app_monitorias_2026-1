from __future__ import annotations

from dataclasses import asdict
from typing import Any

from domain.models import ExerciseProgress, FeedbackRecord, ParticipantRecord
from services.comment_events import build_comment_event_records
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
        progress = record.exercise_progress[exercise]
        self.remote_sync.sync_progress(
            {
                "participant_id": participant_id,
                "exercise": exercise,
                "payload": self._build_remote_progress_payload(progress),
            }
        )
        comment_events = build_comment_event_records(
            participant_id=record.participant_id,
            public_alias=record.public_alias,
            exercise=exercise,
            progress=progress,
        )
        if comment_events:
            self.remote_sync.sync_comment_events(
                {
                    "participant_id": record.participant_id,
                    "public_alias": record.public_alias,
                    "exercise": exercise,
                    "rows": [event.to_dict() for event in comment_events],
                }
            )
        return record

    def save_feedback(
        self, participant_id: str, exercise: str, payload: dict[str, Any]
    ) -> ParticipantRecord:
        feedback = FeedbackRecord(
            rating=int(payload["rating"]),
            summary=str(payload["summary"]),
            missing_topics=str(payload.get("missing_topics", "")),
            improvement_ideas=str(payload.get("improvement_ideas", "")),
        )
        record = self.store.upsert_feedback(participant_id, exercise, feedback)
        self.remote_sync.sync_feedback(
            {"participant_id": participant_id, "exercise": exercise, "payload": asdict(feedback)}
        )
        return record

    def complete_activity(self, participant_id: str, exercise: str) -> ParticipantRecord:
        record = self.store.mark_completed(participant_id, exercise)
        self.remote_sync.sync_completion({"participant_id": participant_id, "exercise": exercise})
        return record

    def get_record(self, participant_id: str) -> ParticipantRecord | None:
        return self.store.get_participant_by_id(participant_id)

    @staticmethod
    def _build_remote_progress_payload(progress: ExerciseProgress) -> dict[str, object]:
        progress_payload = asdict(progress)
        return {
            "dataset_comment": progress_payload["dataset_comment"],
            "analytics_comment": progress_payload["analytics_comment"],
            "prediction_reflection": progress_payload["prediction_reflection"],
            "prediction_inputs": progress_payload["prediction_inputs"],
            "prediction_output": progress_payload["prediction_output"],
        }
