from __future__ import annotations

from pathlib import Path

from services.remote_sync import NoopRemoteSyncClient
from services.session_service import SessionService
from services.storage_sqlite import SQLiteStateStore


def test_start_session_uses_sqlite_create_participant(tmp_path: Path) -> None:
    store = SQLiteStateStore(db_path=tmp_path / "state.db")
    service = SessionService(store=store, remote_sync=NoopRemoteSyncClient())

    record = service.start_session({"name": "Ana", "course": "ML"})
    recovered = store.get_participant(record.access_code_display)

    assert recovered is not None
    assert recovered.participant_id == record.participant_id
    assert recovered.profile == {"name": "Ana", "course": "ML"}
    assert recovered.public_alias == "P-001"
