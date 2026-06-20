from __future__ import annotations

import logging
import sqlite3
from pathlib import Path

from services.sqlite_connection import get_connection


LOGGER = logging.getLogger(__name__)
MIGRATION_VERSION = "0001_initial_store_parity"
SUPPORTED_SCHEMA_TABLES = {"embeddings_cache", "projection_cache"}
SUPPORTED_SCHEMA_COLUMN_DEFINITIONS = {
    "comment_type": "TEXT DEFAULT ''",
    "is_test_data": "INTEGER DEFAULT 0",
    "test_batch_id": "TEXT DEFAULT ''",
}


def create_tables(db_path: Path | str | None = None) -> None:
    """Create the SQLite persistence schema used by the app store."""
    conn = get_connection(db_path)
    try:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS schema_migrations(
            version TEXT PRIMARY KEY,
            applied_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS sesiones(
            participant_id TEXT PRIMARY KEY,
            access_code_hash TEXT UNIQUE,
            access_code_display TEXT,
            public_alias TEXT,
            selected_exercise TEXT,
            created_at TEXT,
            updated_at TEXT
        );

        CREATE TABLE IF NOT EXISTS perfil_participante(
            participant_id TEXT PRIMARY KEY,
            profile_json TEXT,
            sexo TEXT,
            edad INTEGER,
            grado TEXT,
            FOREIGN KEY(participant_id)
                REFERENCES sesiones(participant_id)
                ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS respuesta(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            participant_id TEXT NOT NULL,
            exercise TEXT NOT NULL,
            dataset_comment TEXT,
            analytics_comment TEXT,
            prediction_reflection TEXT,
            prediction_inputs TEXT,
            prediction_output TEXT,
            completed_at TEXT,
            updated_at TEXT,
            UNIQUE(participant_id, exercise),
            FOREIGN KEY(participant_id)
                REFERENCES sesiones(participant_id)
                ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS feedback(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            participant_id TEXT NOT NULL,
            exercise TEXT NOT NULL,
            rating INTEGER,
            summary TEXT,
            missing_topics TEXT,
            improvement_ideas TEXT,
            updated_at TEXT,
            UNIQUE(participant_id, exercise),
            FOREIGN KEY(participant_id)
                REFERENCES sesiones(participant_id)
                ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS comment_events(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            participant_id TEXT NOT NULL,
            public_alias TEXT,
            exercise TEXT,
            comment_type TEXT,
            comment_text TEXT,
            clean_comment TEXT,
            comment_hash TEXT,
            updated_at TEXT,
            source_sheet_row_number INTEGER DEFAULT 0,
            is_test_data INTEGER DEFAULT 0,
            test_batch_id TEXT DEFAULT '',
            data_origin TEXT DEFAULT 'app_runtime',
            UNIQUE(participant_id, exercise, comment_type),
            FOREIGN KEY(participant_id)
                REFERENCES sesiones(participant_id)
                ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS embeddings_cache(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            participant_id TEXT,
            exercise TEXT,
            comment_hash TEXT NOT NULL,
            embedding_version TEXT NOT NULL,
            embedding_provider TEXT,
            comment_text TEXT,
            clean_comment TEXT,
            comment_type TEXT DEFAULT '',
            embedding_vector_json TEXT,
            source_updated_at TEXT,
            source_sheet_row_number INTEGER DEFAULT 0,
            is_test_data INTEGER DEFAULT 0,
            test_batch_id TEXT DEFAULT '',
            cache_key TEXT,
            updated_at TEXT,
            UNIQUE(exercise, participant_id, comment_type, comment_hash, embedding_version)
        );

        CREATE TABLE IF NOT EXISTS projection_cache(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            participant_id TEXT,
            exercise TEXT,
            comment_hash TEXT NOT NULL,
            projection_version TEXT NOT NULL,
            embedding_provider TEXT,
            reduction_provider TEXT,
            public_alias TEXT,
            comment_text TEXT,
            clean_comment TEXT,
            comment_type TEXT DEFAULT '',
            x REAL,
            y REAL,
            z REAL,
            source_updated_at TEXT,
            source_sheet_row_number INTEGER DEFAULT 0,
            is_test_data INTEGER DEFAULT 0,
            test_batch_id TEXT DEFAULT '',
            updated_at TEXT,
            UNIQUE(exercise, participant_id, comment_type, comment_hash, projection_version)
        );
        """)

        _ensure_column(conn, "embeddings_cache", "comment_type")
        _ensure_column(conn, "embeddings_cache", "is_test_data")
        _ensure_column(conn, "embeddings_cache", "test_batch_id")
        _ensure_column(conn, "projection_cache", "comment_type")
        _ensure_column(conn, "projection_cache", "is_test_data")
        _ensure_column(conn, "projection_cache", "test_batch_id")
        conn.execute(
            "INSERT OR IGNORE INTO schema_migrations(version) VALUES (?)",
            (MIGRATION_VERSION,),
        )
        conn.commit()
    except sqlite3.Error:
        conn.rollback()
        LOGGER.exception("Could not initialize SQLite schema")
        raise
    finally:
        conn.close()


def _ensure_column(
    conn: sqlite3.Connection,
    table_name: str,
    column_name: str,
) -> None:
    if table_name not in SUPPORTED_SCHEMA_TABLES:
        raise ValueError(f"Unsupported schema table: {table_name}")
    column_definition = SUPPORTED_SCHEMA_COLUMN_DEFINITIONS.get(column_name)
    if column_definition is None:
        raise ValueError(f"Unsupported schema column: {column_name}")

    columns = {
        row["name"]
        for row in conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    }
    if column_name in columns:
        return

    conn.execute(
        f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_definition}"
    )
