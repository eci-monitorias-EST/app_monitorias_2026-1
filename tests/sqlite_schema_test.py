from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from services.sqlite_schema import _ensure_column, create_tables


def _table_names(conn: sqlite3.Connection) -> set[str]:
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table'"
    ).fetchall()
    return {str(row[0]) for row in rows}


def _unique_index_columns(
    conn: sqlite3.Connection, table_name: str
) -> set[tuple[str, ...]]:
    indexes = conn.execute(f"PRAGMA index_list({table_name})").fetchall()
    unique_columns: set[tuple[str, ...]] = set()
    for index in indexes:
        if not index[2]:
            continue
        index_name = str(index[1])
        columns = conn.execute(f"PRAGMA index_info({index_name})").fetchall()
        unique_columns.add(tuple(str(column[2]) for column in columns))
    return unique_columns


def test_create_tables_initializes_store_parity_schema(tmp_path: Path) -> None:
    db_path = tmp_path / "state.db"

    create_tables(db_path)
    create_tables(db_path)

    with sqlite3.connect(db_path) as conn:
        table_names = _table_names(conn)
        migration_count = conn.execute(
            "SELECT COUNT(*) FROM schema_migrations"
        ).fetchone()[0]

    assert {
        "schema_migrations",
        "sesiones",
        "perfil_participante",
        "respuesta",
        "feedback",
        "comment_events",
        "embeddings_cache",
        "projection_cache",
    }.issubset(table_names)
    assert migration_count == 1


def test_cache_tables_keep_comment_metadata_in_unique_keys(tmp_path: Path) -> None:
    db_path = tmp_path / "state.db"
    create_tables(db_path)

    with sqlite3.connect(db_path) as conn:
        embedding_indexes = _unique_index_columns(conn, "embeddings_cache")
        projection_indexes = _unique_index_columns(conn, "projection_cache")

    assert (
        "exercise",
        "participant_id",
        "comment_type",
        "comment_hash",
        "embedding_version",
    ) in embedding_indexes
    assert (
        "exercise",
        "participant_id",
        "comment_type",
        "comment_hash",
        "projection_version",
    ) in projection_indexes


def test_ensure_column_rejects_unsupported_identifiers(tmp_path: Path) -> None:
    db_path = tmp_path / "state.db"
    create_tables(db_path)

    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        with pytest.raises(ValueError, match="Unsupported schema table"):
            _ensure_column(
                conn,
                "unknown_table",
                "comment_type",
            )
        with pytest.raises(ValueError, match="Unsupported schema column"):
            _ensure_column(
                conn,
                "embeddings_cache",
                "unsafe_column",
            )
