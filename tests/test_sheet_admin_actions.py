from __future__ import annotations

import hashlib
import importlib.util
from argparse import Namespace
from pathlib import Path
from typing import Any

import pytest
import requests


def _load_sheet_admin_actions_module() -> Any:
    module_path = Path(__file__).resolve().parents[1] / "app_scripts_utils" / "sheet_admin_actions.py"
    spec = importlib.util.spec_from_file_location("sheet_admin_actions_module", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("No se pudo cargar sheet_admin_actions.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_webapp_client_module() -> Any:
    module_path = Path(__file__).resolve().parents[1] / "app_scripts_utils" / "webapp_client.py"
    spec = importlib.util.spec_from_file_location("webapp_client_module_for_admin", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("No se pudo cargar webapp_client.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_build_legacy_row_selectors_from_snapshot_detects_feedback_legacy_fields() -> None:
    module = _load_sheet_admin_actions_module()
    snapshot_payload = {
        "sheets": {
            "respuestas": {
                "rows": [
                    {
                        "_sheet_row_number": 7,
                        "participant_id": "p-001",
                        "exercise": "credit_approval",
                        "que_parecio": "Muy útil",
                        "que_hubiera_gustado": "Más ejemplos",
                    },
                    {
                        "_sheet_row_number": 8,
                        "participant_id": "p-002",
                        "exercise": "default_risk",
                        "dataset_comment": "Sin legacy",
                    },
                ]
            }
        }
    }

    selectors = module.build_legacy_row_selectors_from_snapshot(
        snapshot_payload,
        source_sheet="respuestas",
    )

    assert selectors == [
        {
            "row_number": 7,
            "participant_id": "p-001",
            "exercise": "credit_approval",
            "legacy_fields": ["que_hubiera_gustado", "que_parecio"],
        }
    ]


def test_webapp_client_posts_fix_legacy_rows_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    module = _load_webapp_client_module()
    captured: dict[str, Any] = {}

    class _ResponseStub:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, Any]:
            return {"status": "success", "action": "fix_legacy_rows"}

    def _fake_post(url: str, *, json: dict[str, Any], timeout: int) -> _ResponseStub:
        captured["url"] = url
        captured["json"] = json
        captured["timeout"] = timeout
        return _ResponseStub()

    monkeypatch.setattr(requests, "post", _fake_post)

    client = module.WebappSyncClient(
        url="https://example.test/webapp",
        token="token-123",
        timeout=15,
    )

    response = client.fix_legacy_rows(
        source_sheet="respuestas",
        dry_run=True,
        legacy_row_selectors=[{"row_number": 7, "participant_id": "p-001"}],
    )

    assert response == {"status": "success", "action": "fix_legacy_rows"}
    assert captured == {
        "url": "https://example.test/webapp",
        "json": {
            "token": "token-123",
            "accion": "fix_legacy_rows",
            "source_sheet": "respuestas",
            "dry_run": True,
            "legacy_row_selectors": [{"row_number": 7, "participant_id": "p-001"}],
        },
        "timeout": 15,
    }


def test_build_archive_legacy_rows_payload_requires_confirm_phrase_on_execute(tmp_path: Path) -> None:
    module = _load_sheet_admin_actions_module()
    selector_file = tmp_path / "selectors.json"
    selector_file.write_text(
        '[{"row_number": 10, "participant_id": "p-010", "exercise": "credit_approval"}]',
        encoding="utf-8",
    )
    args = Namespace(
        source_sheet="respuestas",
        archive_reason="legacy_cleanup",
        execute=True,
        confirm_phrase=None,
        snapshot=None,
        selector_file=selector_file,
        row_numbers=[],
        participant_ids=[],
        selector_exercise="",
    )

    with pytest.raises(ValueError, match="confirm_phrase inválido"):
        module.build_archive_legacy_rows_payload(args)


def test_build_clear_sheet_rows_payload_includes_filters_and_confirm_phrase() -> None:
    module = _load_sheet_admin_actions_module()
    args = Namespace(
        sheet="projection_cache",
        execute=True,
        confirm_phrase="CLEAR_SHEET_ROWS",
        row_numbers=[4, 5],
        participant_ids=["p-001"],
        exercise="credit_approval",
        test_batch_id="batch-123",
        data_origin="projection_backfill",
        projection_version="v2",
        embedding_version="",
        only_legacy=False,
    )

    payload = module.build_clear_sheet_rows_payload(args)

    assert payload == {
        "target_sheet": "projection_cache",
        "dry_run": False,
        "row_filters": {
            "row_numbers": [4, 5],
            "participant_ids": ["p-001"],
            "exercise": "credit_approval",
            "test_batch_id": "batch-123",
            "data_origin": "projection_backfill",
            "projection_version": "v2",
            "embedding_version": "",
            "only_legacy": False,
        },
        "confirm_phrase": "CLEAR_SHEET_ROWS",
    }


def test_build_rebuild_projection_cache_payload_normalizes_rows_file(tmp_path: Path) -> None:
    module = _load_sheet_admin_actions_module()
    rows_file = tmp_path / "projection_rows.json"
    rows_file.write_text(
        (
            '{"rows": ['
            '{"participant_id": "p-001", "public_alias": "A", "clean_comment": "comentario base", "x": 1.0, "y": 2.0, "z": 3.0}'
            ']}'
        ),
        encoding="utf-8",
    )
    args = Namespace(
        rows_file=rows_file,
        exercise="credit_approval",
        projection_version="projection-v3",
        embedding_provider="minilm",
        reduction_provider="umap",
        append_only=False,
        execute=False,
        confirm_phrase=None,
    )

    payload = module.build_rebuild_projection_cache_payload(args)

    assert payload["exercise"] == "credit_approval"
    assert payload["projection_version"] == "projection-v3"
    assert payload["replace_existing_scope"] is True
    assert payload["dry_run"] is True
    assert payload["rows"] == [
        {
            "participant_id": "p-001",
            "public_alias": "A",
            "clean_comment": "comentario base",
            "comment_hash": hashlib.sha256("comentario base".encode("utf-8")).hexdigest(),
            "x": 1.0,
            "y": 2.0,
            "z": 3.0,
            "exercise": "credit_approval",
            "projection_version": "projection-v3",
            "embedding_provider": "minilm",
            "reduction_provider": "umap",
        }
    ]


def test_run_command_supports_local_only_mode(tmp_path: Path) -> None:
    module = _load_sheet_admin_actions_module()
    rows_file = tmp_path / "embeddings_rows.json"
    rows_file.write_text(
        (
            '{"rows": ['
            '{"participant_id": "p-001", "comment_text": "texto", "embedding_vector": [0.1, 0.2]}'
            ']}'
        ),
        encoding="utf-8",
    )
    args = Namespace(
        command="backfill-embeddings-cache",
        no_request=True,
        rows_file=rows_file,
        exercise="credit_approval",
        embedding_version="emb-v1",
        embedding_provider="minilm",
        execute=False,
    )

    result = module.run_command(args)

    assert result == {
        "status": "local_only",
        "action": "backfill_embeddings_cache",
            "payload": {
                "dry_run": True,
                "rows": [
                    {
                        "participant_id": "p-001",
                        "comment_hash": hashlib.sha256("texto".encode("utf-8")).hexdigest(),
                        "comment_text": "texto",
                        "embedding_vector": [0.1, 0.2],
                        "exercise": "credit_approval",
                        "embedding_version": "emb-v1",
                        "embedding_provider": "minilm",
                }
            ],
        },
    }


def test_webapp_client_posts_query_embeddings_cache_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    module = _load_webapp_client_module()
    captured: dict[str, Any] = {}

    class _ResponseStub:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, Any]:
            return {"status": "success", "rows": []}

    def _fake_post(url: str, *, json: dict[str, Any], timeout: int) -> _ResponseStub:
        captured["url"] = url
        captured["json"] = json
        captured["timeout"] = timeout
        return _ResponseStub()

    monkeypatch.setattr(requests, "post", _fake_post)

    client = module.WebappSyncClient(url="https://example.test/webapp", token="token-123", timeout=15)

    response = client.query_embeddings_cache(
        exercise="credit_approval",
        embedding_version="emb-v1",
        comment_hashes=["hash-1"],
    )

    assert response == {"status": "success", "rows": []}
    assert captured == {
        "url": "https://example.test/webapp",
        "json": {
            "token": "token-123",
            "accion": "query_embeddings_cache",
            "exercise": "credit_approval",
            "embedding_version": "emb-v1",
            "comment_hashes": ["hash-1"],
        },
        "timeout": 15,
    }
