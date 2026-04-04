from __future__ import annotations

import hashlib
import json
import secrets
from pathlib import Path
from typing import Any

from domain.models import CompletedComment, ExerciseProgress, FeedbackRecord, ParticipantRecord, utc_now_iso
from services.comment_events import COMMENT_TYPE_LABELS, build_comment_event_records
from services.configuration import load_app_config
from services.submission_validation import SubmissionValidationService


class JsonStateStore:
    ACCESS_CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    ACCESS_CODE_GROUP_LENGTH = 4
    ACCESS_CODE_GROUP_COUNT = 3

    def __init__(self, path: Path | None = None) -> None:
        config = load_app_config()
        self._submission_validation = SubmissionValidationService()
        self.path = path or config.resolve_path(
            config.persistence.get("local_state_path", "data/processed/app_state.json")
        )
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self._save_raw({"participants": {}, "metadata": {"version": 1}})

    def _load_raw(self) -> dict[str, Any]:
        return json.loads(self.path.read_text(encoding="utf-8"))

    def _save_raw(self, payload: dict[str, Any]) -> None:
        self.path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    @staticmethod
    def normalize_access_code(value: str) -> str:
        return "".join(character for character in value.upper() if character.isalnum())

    @classmethod
    def hash_access_code(cls, value: str) -> str:
        normalized = cls.normalize_access_code(value)
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    @classmethod
    def normalize_access_key(cls, value: str) -> str:
        return cls.normalize_access_code(value)

    @classmethod
    def hash_access_key(cls, value: str) -> str:
        return cls.hash_access_code(value)

    @classmethod
    def generate_access_code(cls) -> str:
        groups = [
            "".join(secrets.choice(cls.ACCESS_CODE_ALPHABET) for _ in range(cls.ACCESS_CODE_GROUP_LENGTH))
            for _ in range(cls.ACCESS_CODE_GROUP_COUNT)
        ]
        return "-".join(groups)

    def _load_records(self) -> dict[str, ParticipantRecord]:
        payload = self._load_raw()
        return {
            key: ParticipantRecord.from_dict(value)
            for key, value in payload.get("participants", {}).items()
        }

    def _save_records(self, records: dict[str, ParticipantRecord]) -> None:
        self._save_raw(
            {
                "participants": {key: value.to_dict() for key, value in records.items()},
                "metadata": {"version": 1, "participants": len(records)},
            }
        )

    def _generate_unique_access_code(self, records: dict[str, ParticipantRecord]) -> tuple[str, str]:
        existing_hashes = {record.access_code_hash for record in records.values() if record.access_code_hash}
        for _ in range(32):
            access_code_display = self.generate_access_code()
            access_code_hash = self.hash_access_code(access_code_display)
            if access_code_hash not in existing_hashes:
                return access_code_display, access_code_hash
        raise RuntimeError("No fue posible generar un código de acceso único.")

    def create_participant(self, profile: dict[str, Any]) -> ParticipantRecord:
        records = self._load_records()
        access_code_display, access_code_hash = self._generate_unique_access_code(records)
        public_alias = f"P-{len(records) + 1:03d}"
        record = ParticipantRecord(
            participant_id=secrets.token_hex(6),
            access_code_hash=access_code_hash,
            public_alias=public_alias,
            profile=dict(profile),
            access_code_display=access_code_display,
        )
        records[access_code_hash] = record
        self._save_records(records)
        return record

    def update_profile(self, participant_id: str, profile: dict[str, Any]) -> ParticipantRecord:
        records = self._load_records()
        for record in records.values():
            if record.participant_id == participant_id:
                record.profile.update(profile)
                record.updated_at = utc_now_iso()
                self._save_records(records)
                return record
        raise KeyError(f"Participant not found: {participant_id}")

    def upsert_participant(self, access_key: str, profile: dict[str, Any]) -> ParticipantRecord:
        access_hash = self.hash_access_code(access_key)
        records = self._load_records()
        record = records.get(access_hash)
        if record is None:
            normalized_access_code = self.normalize_access_code(access_key)
            access_code_display = normalized_access_code or access_key.strip().upper()
            public_alias = f"P-{len(records) + 1:03d}"
            record = ParticipantRecord(
                participant_id=secrets.token_hex(6),
                access_code_hash=access_hash,
                public_alias=public_alias,
                profile=dict(profile),
                access_code_display=access_code_display,
            )
            records[access_hash] = record
        else:
            record.profile.update(profile)
        self._save_records(records)
        return records[access_hash]

    def get_participant(self, access_code: str) -> ParticipantRecord | None:
        access_hash = self.hash_access_code(access_code)
        records = self._load_records()
        record = records.get(access_hash)
        if record is not None:
            return record
        for candidate in records.values():
            if candidate.access_code_hash == access_hash:
                return candidate
        return None

    def get_participant_by_id(self, participant_id: str) -> ParticipantRecord | None:
        records = self._load_records()
        for record in records.values():
            if record.participant_id == participant_id:
                return record
        return None

    def select_exercise(self, participant_id: str, exercise: str) -> ParticipantRecord:
        records = self._load_records()
        for record in records.values():
            if record.participant_id == participant_id:
                record.selected_exercise = exercise
                self._save_records(records)
                return record
        raise KeyError(f"Participant not found: {participant_id}")

    def upsert_exercise_progress(
        self, participant_id: str, exercise: str, payload: dict[str, Any]
    ) -> ParticipantRecord:
        records = self._load_records()
        for record in records.values():
            if record.participant_id == participant_id:
                record.upsert_progress(exercise, payload)
                self._save_records(records)
                return record
        raise KeyError(f"Participant not found: {participant_id}")

    def upsert_feedback(
        self, participant_id: str, exercise: str, feedback: FeedbackRecord
    ) -> ParticipantRecord:
        records = self._load_records()
        for record in records.values():
            if record.participant_id == participant_id:
                record.set_feedback(exercise, feedback)
                self._save_records(records)
                return record
        raise KeyError(f"Participant not found: {participant_id}")

    def mark_completed(self, participant_id: str, exercise: str) -> ParticipantRecord:
        records = self._load_records()
        for record in records.values():
            if record.participant_id == participant_id:
                record.mark_completed(exercise)
                self._save_records(records)
                return record
        raise KeyError(f"Participant not found: {participant_id}")

    def list_completed_comments(self, exercise: str, current_participant_id: str) -> list[CompletedComment]:
        comments: list[CompletedComment] = []
        for record in self._load_records().values():
            progress = record.exercise_progress.get(exercise)
            if progress is None or not progress.prediction_output:
                continue
            events = build_comment_event_records(
                participant_id=record.participant_id,
                public_alias=record.public_alias,
                exercise=exercise,
                progress=progress,
                validator=self._submission_validation,
            )
            comments.extend(
                CompletedComment(
                    participant_id=event.participant_id,
                    public_alias=event.public_alias,
                    exercise=event.exercise,
                    combined_comment=event.comment_text,
                    current_user=record.participant_id == current_participant_id,
                    clean_comment=event.clean_comment,
                    comment_hash=event.comment_hash,
                    source_updated_at=event.updated_at,
                    source_sheet_row_number=event.source_sheet_row_number,
                    comment_type=event.comment_type,
                    comment_type_label=COMMENT_TYPE_LABELS.get(event.comment_type, event.comment_type),
                )
                for event in events
            )
        return comments
