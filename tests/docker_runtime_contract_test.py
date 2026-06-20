from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]


def read_project_file(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text(encoding="utf-8")


def load_compose_config() -> dict[str, Any]:
    return yaml.safe_load(read_project_file("compose.yaml"))


def test_dockerfile_uses_python_312_streamlit_port_and_non_root_user() -> None:
    dockerfile = read_project_file("Dockerfile")

    assert "python3.12" in dockerfile
    assert "USER appuser" in dockerfile
    assert "EXPOSE 8501" in dockerfile
    assert "app/main.py" in dockerfile
    assert "--server.address=0.0.0.0" in dockerfile


def test_compose_configures_sqlite_runtime_volume_and_port_binding() -> None:
    compose_config = load_compose_config()
    app_service = compose_config["services"]["app"]

    assert app_service["build"] == "."
    assert app_service["environment"]["PERSISTENCE_STORE"] == "sqlite"
    assert app_service["environment"]["SQLITE_PATH"] == "/app/data/processed/app.db"
    assert app_service["ports"] == ["${STREAMLIT_PORT:-8501}:8501"]
    assert "monitorias_sqlite_data:/app/data/processed" in app_service["volumes"]
    assert "monitorias_sqlite_data" in compose_config["volumes"]


def test_readme_documents_docker_sqlite_contract_and_replica_caveat() -> None:
    readme = read_project_file("README.md")

    assert "docker compose up --build" in readme
    assert "PERSISTENCE_STORE=sqlite" in readme
    assert "SQLITE_PATH=/app/data/processed/app.db" in readme
    assert "single writable replica" in readme
    assert "Apps Script" in readme
