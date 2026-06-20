from __future__ import annotations

from pathlib import Path

from services.sqlite_connection import get_connection


def test_database_connection_uses_requested_path_and_foreign_keys(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "nested" / "state.db"

    conn = get_connection(db_path)
    try:
        foreign_keys_enabled = conn.execute("PRAGMA foreign_keys").fetchone()[0]
    finally:
        conn.close()

    assert db_path.exists()
    assert foreign_keys_enabled == 1
