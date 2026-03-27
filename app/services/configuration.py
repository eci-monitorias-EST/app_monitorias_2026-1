from __future__ import annotations

import json
import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any


ROOT_DIR = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_PATH = ROOT_DIR / "app" / "config" / "app.yaml"


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
    def comments(self) -> dict[str, Any]:
        return self.raw.get("comments", {})

    @property
    def modeling(self) -> dict[str, Any]:
        return self.raw.get("modeling", {})

    def resolve_path(self, value: str) -> Path:
        path = Path(value)
        return path if path.is_absolute() else ROOT_DIR / path


def _load_yaml_or_json(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    try:
        import yaml  # type: ignore

        return yaml.safe_load(text)
    except Exception:
        return json.loads(text)


@lru_cache(maxsize=1)
def load_app_config() -> AppConfig:
    configured_path = os.getenv("APP_CONFIG_YAML")
    path = Path(configured_path) if configured_path else DEFAULT_CONFIG_PATH
    if not path.is_absolute():
        path = ROOT_DIR / path
    return AppConfig(raw=_load_yaml_or_json(path))
