from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

import pytest
import requests


def _load_webapp_client_module() -> Any:
    module_path = Path(__file__).resolve().parents[1] / "app_scripts_utils" / "webapp_client.py"
    spec = importlib.util.spec_from_file_location("webapp_client_module", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("No se pudo cargar webapp_client.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_snapshot_export_module() -> Any:
    script_path = Path(__file__).resolve().parents[1] / "app_scripts_utils" / "sheet_snapshot_export.py"
    spec = importlib.util.spec_from_file_location("sheet_snapshot_export_script", script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("No se pudo cargar sheet_snapshot_export.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_normalize_sheet_names_deduplicates_and_requires_values() -> None:
    module = _load_snapshot_export_module()

    assert module.normalize_sheet_names([" sesiones ", "respuestas", "sesiones", ""]) == [
        "sesiones",
        "respuestas",
    ]

    with pytest.raises(ValueError, match="al menos una hoja"):
        module.normalize_sheet_names(["", "   "])


def test_normalize_limit_rows_caps_to_maximum() -> None:
    module = _load_snapshot_export_module()

    assert module.normalize_limit_rows(50) == 50
    assert module.normalize_limit_rows(999) == module.MAX_LIMIT_ROWS

    with pytest.raises(ValueError, match="mayor que cero"):
        module.normalize_limit_rows(0)


def test_webapp_client_exports_sheet_snapshot_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    webapp_client_module = _load_webapp_client_module()
    captured: dict[str, Any] = {}

    class _ResponseStub:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, Any]:
            return {"status": "success", "action": "export_sheet_snapshot"}

    def _fake_post(url: str, *, json: dict[str, Any], timeout: int) -> _ResponseStub:
        captured["url"] = url
        captured["json"] = json
        captured["timeout"] = timeout
        return _ResponseStub()

    monkeypatch.setattr(requests, "post", _fake_post)

    client = webapp_client_module.WebappSyncClient(
        url="https://example.test/webapp",
        token="token-123",
        timeout=12,
    )
    response = client.export_sheet_snapshot(sheet_names=["sesiones", "feedback"], limit_rows=150)

    assert response == {"status": "success", "action": "export_sheet_snapshot"}
    assert captured == {
        "url": "https://example.test/webapp",
        "json": {
            "token": "token-123",
            "accion": "export_sheet_snapshot",
            "sheet_names": ["sesiones", "feedback"],
            "limit_rows": 150,
        },
        "timeout": 12,
    }


def test_save_snapshot_artifacts_writes_manifest_json_and_sheet_csv(tmp_path: Path) -> None:
    module = _load_snapshot_export_module()
    payload = {
        "status": "success",
        "sheets": {
            "sesiones": {
                "sheet_name": "sesiones",
                "column_count": 2,
                "columns": ["participant_id", "public_alias"],
                "total_rows": 1,
                "returned_rows": 1,
                "truncated": False,
                "rows": [{"participant_id": "p-001", "public_alias": "TEST-001"}],
            }
        },
    }

    result = module.save_snapshot_artifacts(
        payload,
        output_dir=tmp_path,
        snapshot_label="demo batch",
        export_format="both",
    )

    manifest_path = tmp_path / "demo_batch-manifest.json"
    sheet_json_path = tmp_path / "demo_batch-sesiones.json"
    sheet_csv_path = tmp_path / "demo_batch-sesiones.csv"

    assert manifest_path.exists()
    assert sheet_json_path.exists()
    assert sheet_csv_path.exists()
    assert result["files"]["json"] == [str(manifest_path), str(sheet_json_path)]
    assert result["files"]["csv"] == [str(sheet_csv_path)]
    assert '"participant_id": "p-001"' in manifest_path.read_text(encoding="utf-8")
    csv_lines = sheet_csv_path.read_text(encoding="utf-8").splitlines()
    assert csv_lines == ["participant_id,public_alias", "p-001,TEST-001"]


def test_export_snapshot_normalizes_inputs_before_calling_client() -> None:
    module = _load_snapshot_export_module()
    captured: dict[str, Any] = {}

    class _ClientStub:
        def export_sheet_snapshot(self, *, sheet_names: list[str], limit_rows: int) -> dict[str, Any]:
            captured["sheet_names"] = sheet_names
            captured["limit_rows"] = limit_rows
            return {"status": "success", "sheets": {}}

    response = module.export_snapshot(
        _ClientStub(),
        sheet_names=["sesiones", "sesiones", "feedback"],
        limit_rows=999,
    )

    assert response == {"status": "success", "sheets": {}}
    assert captured == {
        "sheet_names": ["sesiones", "feedback"],
        "limit_rows": module.MAX_LIMIT_ROWS,
    }
