from __future__ import annotations

from pathlib import Path

import pytest

from services.app_container import AppContainer
from services.configuration import AppConfig
from services.remote_sync import NoopRemoteSyncClient
from services.storage import JsonStateStore
from services.storage_sqlite import SQLiteStateStore


def test_app_container_uses_sqlite_store_by_default(tmp_path: Path) -> None:
    db_path = tmp_path / "app.db"
    config = AppConfig(raw={"persistence": {"sqlite_path": str(db_path)}})

    container = AppContainer(config=config)

    assert isinstance(container.store, SQLiteStateStore)
    assert container.store.db_path == db_path
    assert db_path.exists()


def test_app_container_uses_json_store_only_when_configured(tmp_path: Path) -> None:
    state_path = tmp_path / "state.json"
    config = AppConfig(
        raw={
            "persistence": {
                "store": "json",
                "local_state_path": str(state_path),
                "sync_to_apps_script": False,
            }
        }
    )

    container = AppContainer(config=config)

    assert isinstance(container.store, JsonStateStore)
    assert container.store.path == state_path


def test_app_container_does_not_require_apps_script_secrets_by_default(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    config = AppConfig(raw={"persistence": {"sqlite_path": str(tmp_path / "app.db")}})

    monkeypatch.setattr(
        "services.remote_sync.get_script_url",
        lambda: pytest.fail("Apps Script URL should not be read in default DB mode"),
    )
    monkeypatch.setattr(
        "services.remote_sync.get_form_token",
        lambda: pytest.fail("Apps Script token should not be read in default DB mode"),
    )

    container = AppContainer(config=config)

    assert isinstance(container.remote_sync, NoopRemoteSyncClient)
