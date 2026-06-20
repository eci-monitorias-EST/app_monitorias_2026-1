from __future__ import annotations

from collections.abc import Callable, Sequence
import hashlib
import json
import logging
import secrets
import sqlite3
from pathlib import Path
from typing import Any, TypedDict, cast

from domain.models import (
    CompletedComment,
    ExerciseProgress,
    FeedbackRecord,
    ParticipantRecord,
    utc_now_iso,
)
from services.comment_events import COMMENT_TYPE_LABELS, build_comment_event_records
from services.sqlite_connection import get_connection
from services.sqlite_schema import create_tables
from services.submission_validation import SubmissionValidationService


LOGGER = logging.getLogger(__name__)

EMBEDDINGS_CACHE_COLUMNS = (
    "participant_id",
    "exercise",
    "comment_hash",
    "embedding_version",
    "embedding_provider",
    "comment_type",
    "comment_text",
    "clean_comment",
    "embedding_vector_json",
)
PROJECTION_CACHE_COLUMNS = (
    "participant_id",
    "public_alias",
    "exercise",
    "comment_hash",
    "projection_version",
    "embedding_provider",
    "reduction_provider",
    "comment_type",
    "comment_text",
    "clean_comment",
    "x",
    "y",
    "z",
)
CACHE_TABLES = {
    "embeddings_cache": ("embedding_version", EMBEDDINGS_CACHE_COLUMNS),
    "projection_cache": ("projection_version", PROJECTION_CACHE_COLUMNS),
}


class EmbeddingCacheRow(TypedDict, total=False):
    participant_id: str
    exercise: str
    comment_hash: str
    embedding_version: str
    embedding_provider: str
    comment_type: str
    comment_text: str
    clean_comment: str
    embedding_vector_json: str


class ProjectionCacheRow(TypedDict, total=False):
    participant_id: str
    public_alias: str
    exercise: str
    comment_hash: str
    projection_version: str
    embedding_provider: str
    reduction_provider: str
    comment_type: str
    comment_text: str
    clean_comment: str
    x: float
    y: float
    z: float


CacheRow = EmbeddingCacheRow | ProjectionCacheRow


class SQLiteStateStore:
    """SQLite-backed state store that mirrors JsonStateStore behavior."""

    ACCESS_CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    ACCESS_CODE_GROUP_LENGTH = 4
    ACCESS_CODE_GROUP_COUNT = 3

    def __init__(self, db_path: Path | str | None = None) -> None:
        self.db_path = Path(db_path) if db_path is not None else None
        self._submission_validation = SubmissionValidationService()
        create_tables(self.db_path)

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
            "".join(
                secrets.choice(cls.ACCESS_CODE_ALPHABET)
                for _ in range(cls.ACCESS_CODE_GROUP_LENGTH)
            )
            for _ in range(cls.ACCESS_CODE_GROUP_COUNT)
        ]
        return "-".join(groups)

    def create_participant(self, profile: dict[str, Any]) -> ParticipantRecord:
        try:
            with self._connect() as conn:
                access_code_display, access_code_hash = (
                    self._generate_unique_access_code(conn)
                )
                record = ParticipantRecord(
                    participant_id=secrets.token_hex(6),
                    access_code_hash=access_code_hash,
                    public_alias=f"P-{self._participant_count(conn) + 1:03d}",
                    profile=dict(profile),
                    access_code_display=access_code_display,
                )
                self._save_record(conn, record)
                conn.commit()
                return record
        except sqlite3.Error:
            LOGGER.exception("Could not create SQLite participant")
            raise

    def upsert_participant(
        self, access_key: str, profile: dict[str, Any]
    ) -> ParticipantRecord:
        access_hash = self.hash_access_key(access_key)
        try:
            with self._connect() as conn:
                record = self._get_by_access_hash(conn, access_hash)
                if record is None:
                    public_alias = f"P-{self._participant_count(conn) + 1:03d}"
                    record = ParticipantRecord(
                        participant_id=secrets.token_hex(6),
                        access_code_hash=access_hash,
                        public_alias=public_alias,
                        profile=dict(profile),
                        access_code_display=self.normalize_access_key(access_key)
                        or access_key.strip().upper(),
                    )
                else:
                    record.profile.update(profile)
                    record.updated_at = utc_now_iso()
                self._save_record(conn, record)
                conn.commit()
                return record
        except sqlite3.Error:
            LOGGER.exception("Could not upsert SQLite participant")
            raise

    def update_profile(
        self, participant_id: str, profile: dict[str, Any]
    ) -> ParticipantRecord:
        def apply_profile_update(record: ParticipantRecord) -> None:
            record.profile.update(profile)
            record.updated_at = utc_now_iso()

        return self._mutate_record(
            participant_id,
            apply_profile_update,
            "update SQLite participant profile",
        )

    def get_participant(self, access_code: str) -> ParticipantRecord | None:
        try:
            with self._connect() as conn:
                return self._get_by_access_hash(
                    conn, self.hash_access_code(access_code)
                )
        except sqlite3.Error:
            LOGGER.exception("Could not get SQLite participant by access code")
            raise

    def get_participant_by_id(self, participant_id: str) -> ParticipantRecord | None:
        try:
            with self._connect() as conn:
                return self._get_by_id(conn, participant_id)
        except sqlite3.Error:
            LOGGER.exception("Could not get SQLite participant by id")
            raise

    def select_exercise(self, participant_id: str, exercise: str) -> ParticipantRecord:
        def apply_exercise_selection(record: ParticipantRecord) -> None:
            record.selected_exercise = exercise
            record.updated_at = utc_now_iso()

        return self._mutate_record(
            participant_id,
            apply_exercise_selection,
            "select SQLite exercise",
        )

    def upsert_exercise_progress(
        self, participant_id: str, exercise: str, payload: dict[str, Any]
    ) -> ParticipantRecord:
        def apply_progress_update(record: ParticipantRecord) -> None:
            record.upsert_progress(exercise, payload)

        return self._mutate_record(
            participant_id,
            apply_progress_update,
            "upsert SQLite exercise progress",
        )

    def upsert_feedback(
        self, participant_id: str, exercise: str, feedback: FeedbackRecord
    ) -> ParticipantRecord:
        def apply_feedback_update(record: ParticipantRecord) -> None:
            record.set_feedback(exercise, feedback)

        return self._mutate_record(
            participant_id,
            apply_feedback_update,
            "upsert SQLite feedback",
        )

    def mark_completed(self, participant_id: str, exercise: str) -> ParticipantRecord:
        def apply_completion(record: ParticipantRecord) -> None:
            record.mark_completed(exercise)

        return self._mutate_record(
            participant_id,
            apply_completion,
            "mark SQLite progress completed",
        )

    def list_completed_comments(
        self, exercise: str, current_participant_id: str
    ) -> list[CompletedComment]:
        try:
            comments: list[CompletedComment] = []
            with self._connect() as conn:
                for record in self._list_records(conn):
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
                            current_user=record.participant_id
                            == current_participant_id,
                            clean_comment=event.clean_comment,
                            comment_hash=event.comment_hash,
                            source_updated_at=event.updated_at,
                            source_sheet_row_number=event.source_sheet_row_number,
                            comment_type=event.comment_type,
                            comment_type_label=COMMENT_TYPE_LABELS.get(
                                event.comment_type, event.comment_type
                            ),
                        )
                        for event in events
                    )
            return comments
        except sqlite3.Error:
            LOGGER.exception("Could not list SQLite completed comments")
            raise

    def upsert_embeddings_cache(self, rows: list[EmbeddingCacheRow]) -> None:
        self._upsert_cache_rows("embeddings_cache", rows)

    def query_embeddings_cache(
        self, *, exercise: str, embedding_version: str, comment_hashes: list[str]
    ) -> list[EmbeddingCacheRow]:
        return cast(
            list[EmbeddingCacheRow],
            self._query_cache_rows(
                "embeddings_cache",
                exercise,
                embedding_version,
                comment_hashes,
            ),
        )

    def upsert_projection_cache(self, rows: list[ProjectionCacheRow]) -> None:
        self._upsert_cache_rows("projection_cache", rows)

    def query_projection_cache(
        self, *, exercise: str, projection_version: str, comment_hashes: list[str]
    ) -> list[ProjectionCacheRow]:
        return cast(
            list[ProjectionCacheRow],
            self._query_cache_rows(
                "projection_cache",
                exercise,
                projection_version,
                comment_hashes,
            ),
        )

    def _connect(self) -> sqlite3.Connection:
        return get_connection(self.db_path)

    def _mutate_record(
        self,
        participant_id: str,
        mutation: Callable[[ParticipantRecord], None],
        operation: str,
    ) -> ParticipantRecord:
        try:
            with self._connect() as conn:
                record = self._require_record(conn, participant_id)
                mutation(record)
                self._save_record(conn, record)
                conn.commit()
                return record
        except sqlite3.Error:
            LOGGER.exception("Could not %s", operation)
            raise

    def _get_by_access_hash(
        self, conn: sqlite3.Connection, access_hash: str
    ) -> ParticipantRecord | None:
        row = conn.execute(
            "SELECT participant_id FROM sesiones WHERE access_code_hash = ?",
            (access_hash,),
        ).fetchone()
        return (
            None if row is None else self._get_by_id(conn, str(row["participant_id"]))
        )

    def _get_by_id(
        self, conn: sqlite3.Connection, participant_id: str
    ) -> ParticipantRecord | None:
        row = conn.execute(
            "SELECT * FROM sesiones WHERE participant_id = ?",
            (participant_id,),
        ).fetchone()
        return None if row is None else self._record_from_row(conn, row)

    def _require_record(
        self, conn: sqlite3.Connection, participant_id: str
    ) -> ParticipantRecord:
        record = self._get_by_id(conn, participant_id)
        if record is None:
            raise KeyError(f"Participant not found: {participant_id}")
        return record

    def _list_records(self, conn: sqlite3.Connection) -> list[ParticipantRecord]:
        rows = conn.execute("SELECT * FROM sesiones ORDER BY public_alias").fetchall()
        return [self._record_from_row(conn, row) for row in rows]

    def _record_from_row(
        self, conn: sqlite3.Connection, row: sqlite3.Row
    ) -> ParticipantRecord:
        participant_id = str(row["participant_id"])
        return ParticipantRecord(
            participant_id=participant_id,
            access_code_hash=str(row["access_code_hash"] or ""),
            public_alias=str(row["public_alias"] or ""),
            profile=self._load_profile(conn, participant_id),
            access_code_display=str(row["access_code_display"] or ""),
            selected_exercise=row["selected_exercise"],
            exercise_progress=self._load_progress(conn, participant_id),
            created_at=str(row["created_at"] or utc_now_iso()),
            updated_at=str(row["updated_at"] or utc_now_iso()),
        )

    def _participant_count(self, conn: sqlite3.Connection) -> int:
        return int(conn.execute("SELECT COUNT(*) FROM sesiones").fetchone()[0])

    def _generate_unique_access_code(self, conn: sqlite3.Connection) -> tuple[str, str]:
        existing_hashes = {
            str(row["access_code_hash"])
            for row in conn.execute(
                "SELECT access_code_hash FROM sesiones WHERE access_code_hash IS NOT NULL"
            ).fetchall()
        }
        for _ in range(32):
            access_code_display = self.generate_access_code()
            access_code_hash = self.hash_access_code(access_code_display)
            if access_code_hash not in existing_hashes:
                return access_code_display, access_code_hash
        raise RuntimeError("Could not generate a unique SQLite access code.")

    def _load_profile(
        self, conn: sqlite3.Connection, participant_id: str
    ) -> dict[str, Any]:
        row = conn.execute(
            "SELECT profile_json FROM perfil_participante WHERE participant_id = ?",
            (participant_id,),
        ).fetchone()
        if row is None or not row["profile_json"]:
            return {}
        loaded = self._load_json_value(
            str(row["profile_json"]), {}, "participant profile"
        )
        return dict(loaded) if isinstance(loaded, dict) else {}

    def _load_progress(
        self, conn: sqlite3.Connection, participant_id: str
    ) -> dict[str, ExerciseProgress]:
        rows = conn.execute(
            "SELECT * FROM respuesta WHERE participant_id = ?", (participant_id,)
        ).fetchall()
        return {
            str(row["exercise"]): self._progress_from_row(conn, row) for row in rows
        }

    def _progress_from_row(
        self, conn: sqlite3.Connection, row: sqlite3.Row
    ) -> ExerciseProgress:
        participant_id = str(row["participant_id"])
        exercise = str(row["exercise"])
        return ExerciseProgress(
            exercise=exercise,
            dataset_comment=str(row["dataset_comment"] or ""),
            analytics_comment=str(row["analytics_comment"] or ""),
            prediction_reflection=str(row["prediction_reflection"] or ""),
            prediction_inputs=self._load_json_dict(
                row["prediction_inputs"], "prediction inputs"
            ),
            prediction_output=self._load_json_dict(
                row["prediction_output"], "prediction output"
            ),
            feedback=self._load_feedback(conn, participant_id, exercise),
            completed_at=row["completed_at"],
            updated_at=str(row["updated_at"] or utc_now_iso()),
        )

    def _load_feedback(
        self, conn: sqlite3.Connection, participant_id: str, exercise: str
    ) -> FeedbackRecord | None:
        row = conn.execute(
            "SELECT * FROM feedback WHERE participant_id = ? AND exercise = ?",
            (participant_id, exercise),
        ).fetchone()
        if row is None:
            return None
        return FeedbackRecord(
            rating=int(row["rating"] or 0),
            summary=str(row["summary"] or ""),
            missing_topics=str(row["missing_topics"] or ""),
            improvement_ideas=str(row["improvement_ideas"] or ""),
            updated_at=str(row["updated_at"] or utc_now_iso()),
        )

    def _save_record(self, conn: sqlite3.Connection, record: ParticipantRecord) -> None:
        conn.execute(
            """
            INSERT INTO sesiones(
                participant_id, access_code_hash, access_code_display, public_alias,
                selected_exercise, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(participant_id) DO UPDATE SET
                access_code_hash = excluded.access_code_hash,
                access_code_display = excluded.access_code_display,
                public_alias = excluded.public_alias,
                selected_exercise = excluded.selected_exercise,
                updated_at = excluded.updated_at
            """,
            (
                record.participant_id,
                record.access_code_hash,
                record.access_code_display,
                record.public_alias,
                record.selected_exercise,
                record.created_at,
                record.updated_at,
            ),
        )
        self._save_profile(conn, record)
        for progress in record.exercise_progress.values():
            self._save_progress(conn, record.participant_id, progress)

    def _save_profile(
        self, conn: sqlite3.Connection, record: ParticipantRecord
    ) -> None:
        conn.execute(
            """
            INSERT INTO perfil_participante(participant_id, profile_json, sexo, edad, grado)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(participant_id) DO UPDATE SET
                profile_json = excluded.profile_json,
                sexo = excluded.sexo,
                edad = excluded.edad,
                grado = excluded.grado
            """,
            (
                record.participant_id,
                json.dumps(record.profile, ensure_ascii=False),
                record.profile.get("sexo"),
                record.profile.get("age", record.profile.get("edad")),
                record.profile.get("grade", record.profile.get("grado")),
            ),
        )

    def _save_progress(
        self, conn: sqlite3.Connection, participant_id: str, progress: ExerciseProgress
    ) -> None:
        conn.execute(
            """
            INSERT INTO respuesta(
                participant_id, exercise, dataset_comment, analytics_comment,
                prediction_reflection, prediction_inputs, prediction_output,
                completed_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(participant_id, exercise) DO UPDATE SET
                dataset_comment = excluded.dataset_comment,
                analytics_comment = excluded.analytics_comment,
                prediction_reflection = excluded.prediction_reflection,
                prediction_inputs = excluded.prediction_inputs,
                prediction_output = excluded.prediction_output,
                completed_at = excluded.completed_at,
                updated_at = excluded.updated_at
            """,
            (
                participant_id,
                progress.exercise,
                progress.dataset_comment,
                progress.analytics_comment,
                progress.prediction_reflection,
                json.dumps(progress.prediction_inputs, ensure_ascii=False),
                json.dumps(progress.prediction_output, ensure_ascii=False),
                progress.completed_at,
                progress.updated_at,
            ),
        )
        if progress.feedback is not None:
            self._save_feedback(
                conn, participant_id, progress.exercise, progress.feedback
            )

    def _save_feedback(
        self,
        conn: sqlite3.Connection,
        participant_id: str,
        exercise: str,
        feedback: FeedbackRecord,
    ) -> None:
        conn.execute(
            """
            INSERT INTO feedback(
                participant_id, exercise, rating, summary, missing_topics,
                improvement_ideas, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(participant_id, exercise) DO UPDATE SET
                rating = excluded.rating,
                summary = excluded.summary,
                missing_topics = excluded.missing_topics,
                improvement_ideas = excluded.improvement_ideas,
                updated_at = excluded.updated_at
            """,
            (
                participant_id,
                exercise,
                feedback.rating,
                feedback.summary,
                feedback.missing_topics,
                feedback.improvement_ideas,
                feedback.updated_at,
            ),
        )

    def _load_json_dict(self, raw_value: Any, context: str) -> dict[str, Any]:
        loaded = self._load_json_value(str(raw_value or "{}"), {}, context)
        return dict(loaded) if isinstance(loaded, dict) else {}

    def _load_json_value(self, raw_value: str, default: Any, context: str) -> Any:
        try:
            return json.loads(raw_value)
        except json.JSONDecodeError:
            LOGGER.warning("Invalid SQLite JSON payload for %s", context)
            return default

    def _upsert_cache_rows(self, table_name: str, rows: Sequence[CacheRow]) -> None:
        if not rows:
            return
        version_column, columns = self._cache_metadata(table_name)
        placeholders = ", ".join("?" for _ in columns)
        assignments = ", ".join(f"{column} = excluded.{column}" for column in columns)
        sql = (
            f"INSERT INTO {table_name}({', '.join(columns)}) VALUES ({placeholders}) "
            "ON CONFLICT(exercise, participant_id, comment_type, comment_hash, "
            f"{version_column}) DO UPDATE SET {assignments}"
        )
        try:
            with self._connect() as conn:
                conn.executemany(
                    sql, [self._cache_values(row, columns) for row in rows]
                )
                conn.commit()
        except sqlite3.Error:
            LOGGER.exception("Could not upsert SQLite %s rows", table_name)
            raise

    def _query_cache_rows(
        self,
        table_name: str,
        exercise: str,
        version: str,
        comment_hashes: list[str],
    ) -> list[CacheRow]:
        if not comment_hashes:
            return []
        version_column, _ = self._cache_metadata(table_name)
        placeholders = ", ".join("?" for _ in comment_hashes)
        try:
            with self._connect() as conn:
                rows = conn.execute(
                    f"""
                    SELECT * FROM {table_name}
                    WHERE exercise = ? AND {version_column} = ?
                      AND comment_hash IN ({placeholders})
                    ORDER BY participant_id, comment_type
                    """,
                    (exercise, version, *comment_hashes),
                ).fetchall()
                return [cast(CacheRow, dict(row)) for row in rows]
        except sqlite3.Error:
            LOGGER.exception("Could not query SQLite %s rows", table_name)
            raise

    def _cache_metadata(self, table_name: str) -> tuple[str, tuple[str, ...]]:
        metadata = CACHE_TABLES.get(table_name)
        if metadata is None:
            raise ValueError(f"Unsupported cache table: {table_name}")
        return metadata

    def _cache_values(self, row: CacheRow, columns: tuple[str, ...]) -> tuple[Any, ...]:
        return tuple(row.get(column) for column in columns)
