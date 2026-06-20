from __future__ import annotations

import logging
import sqlite3
from pathlib import Path


LOGGER = logging.getLogger(__name__)
DEFAULT_DB_PATH = Path(__file__).resolve().parents[2] / "data" / "processed" / "app.db"


def get_connection(db_path: Path | str | None = None) -> sqlite3.Connection:
    """Open a SQLite connection for the configured application state database."""
    resolved_path = Path(db_path) if db_path is not None else DEFAULT_DB_PATH

    try:
        resolved_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(resolved_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
    except OSError:
        LOGGER.exception(
            "Could not create SQLite database directory: %s", resolved_path.parent
        )
        raise
    except sqlite3.Error:
        LOGGER.exception("Could not open SQLite database: %s", resolved_path)
        raise

    return conn
