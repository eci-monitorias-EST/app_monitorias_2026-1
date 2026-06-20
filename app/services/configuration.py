from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any


ROOT_DIR = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_PATH = ROOT_DIR / "app" / "config" / "app.yaml"
LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class AppConfig:
    raw: dict[str, Any]

    @property
    def app(self) -> dict[str, Any]:
        return self.raw.get("app", {})

    @property
    def persistence(self) -> dict[str, Any]:
        return self.raw.get("persistence", {})

    @property
    def persistence_store(self) -> str:
        configured_store = os.getenv("PERSISTENCE_STORE") or self.persistence.get(
            "store", "sqlite"
        )
        return str(configured_store).strip().lower()

    @property
    def sqlite_path(self) -> Path:
        configured_path = os.getenv("SQLITE_PATH") or self.persistence.get(
            "sqlite_path", "data/processed/app.db"
        )
        return self.resolve_path(str(configured_path))

    @property
    def json_state_path(self) -> Path:
        configured_path = self.persistence.get(
            "local_state_path", "data/processed/app_state.json"
        )
        return self.resolve_path(str(configured_path))

    @property
    def remote_sync_enabled(self) -> bool:
        return bool(self.persistence.get("sync_to_apps_script", False))

    @property
    def comments(self) -> dict[str, Any]:
        return self.raw.get("comments", {})

    @property
    def modeling(self) -> dict[str, Any]:
        return self.raw.get("modeling", {})

    def resolve_path(self, value: str) -> Path:
        path = Path(value)
        return path if path.is_absolute() else ROOT_DIR / path


def _load_yaml_or_json(path: Path) -> dict[str, Any]:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        LOGGER.exception("Could not read app config: %s", path)
        raise RuntimeError(f"Could not read app config: {path}") from exc

    try:
        import yaml  # type: ignore

        parsed = yaml.safe_load(text)
    except ModuleNotFoundError:
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON app config: {path}") from exc
    except yaml.YAMLError as exc:  # type: ignore[name-defined]
        raise ValueError(f"Invalid YAML app config: {path}") from exc

    if not isinstance(parsed, dict):
        raise ValueError(f"App config must be a mapping: {path}")
    return dict(parsed)


@lru_cache(maxsize=1)
def load_app_config() -> AppConfig:
    configured_path = os.getenv("APP_CONFIG_YAML")
    path = Path(configured_path) if configured_path else DEFAULT_CONFIG_PATH
    if not path.is_absolute():
        path = ROOT_DIR / path
    return AppConfig(raw=_load_yaml_or_json(path))
