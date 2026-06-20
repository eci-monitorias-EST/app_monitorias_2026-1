from __future__ import annotations

from pathlib import Path

import pytest

from services.configuration import AppConfig, _load_yaml_or_json


def test_persistence_defaults_to_sqlite_and_remote_sync_disabled() -> None:
    config = AppConfig(raw={"persistence": {}})

    assert config.persistence_store == "sqlite"
    assert config.remote_sync_enabled is False


def test_sqlite_path_uses_environment_override(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    db_path = tmp_path / "runtime.db"
    config = AppConfig(raw={"persistence": {"sqlite_path": "data/processed/app.db"}})

    monkeypatch.setenv("SQLITE_PATH", str(db_path))

    assert config.sqlite_path == db_path


def test_json_state_path_remains_explicit_fallback(tmp_path: Path) -> None:
    state_path = tmp_path / "state.json"
    config = AppConfig(
        raw={
            "persistence": {
                "store": "json",
                "local_state_path": str(state_path),
            }
        }
    )

    assert config.persistence_store == "json"
    assert config.json_state_path == state_path


def test_load_config_rejects_non_mapping_payload(tmp_path: Path) -> None:
    config_path = tmp_path / "app.yaml"
    config_path.write_text("['not', 'a', 'mapping']", encoding="utf-8")

    with pytest.raises(ValueError, match="must be a mapping"):
        _load_yaml_or_json(config_path)


def test_load_config_reports_missing_file(tmp_path: Path) -> None:
    missing_path = tmp_path / "missing.yaml"

    with pytest.raises(RuntimeError, match="Could not read app config"):
        _load_yaml_or_json(missing_path)
