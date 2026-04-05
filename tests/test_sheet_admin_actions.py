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


def test_build_cascade_step_payload_dry_run_excludes_confirm_phrase() -> None:
    module = _load_sheet_admin_actions_module()

    payload = module.build_cascade_step_payload(
        target_sheet="respuestas",
        participant_ids=["p-042"],
        dry_run=True,
    )

    assert payload["target_sheet"] == "respuestas"
    assert payload["dry_run"] is True
    assert payload["row_filters"]["participant_ids"] == ["p-042"]
    assert "confirm_phrase" not in payload


def test_build_cascade_step_payload_execute_uses_clear_sheet_rows_phrase() -> None:
    # The Apps Script expects CLEAR_SHEET_ROWS for the clear_sheet_rows action,
    # NOT the cascade-level phrase. This was a bug in the original implementation.
    module = _load_sheet_admin_actions_module()

    payload = module.build_cascade_step_payload(
        target_sheet="sesiones",
        participant_ids=["p-042"],
        dry_run=False,
    )

    assert payload["dry_run"] is False
    assert payload["confirm_phrase"] == "CLEAR_SHEET_ROWS"


def test_build_cascade_step_payload_all_participants_sends_empty_list() -> None:
    module = _load_sheet_admin_actions_module()

    payload = module.build_cascade_step_payload(
        target_sheet="sesiones",
        participant_ids=[],
        dry_run=True,
    )

    assert payload["row_filters"]["participant_ids"] == []


def test_run_cascade_delete_participant_dry_run_calls_all_primary_sheets(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_sheet_admin_actions_module()
    webapp_module = _load_webapp_client_module()
    calls: list[tuple[str, dict[str, Any]]] = []

    class _FakeClient:
        def run_admin_action(self, action: str, payload: dict[str, Any]) -> dict[str, Any]:
            calls.append((action, payload))
            return {"status": "success", "dry_run_affected": 1}

    args = Namespace(
        participant_id="p-042",
        execute=False,
        confirm_phrase=None,
        include_caches=False,
    )

    result = module.run_cascade_delete_participant(args, client=_FakeClient())

    assert result["dry_run"] is True
    assert result["participant_id"] == "p-042"
    assert result["include_caches"] is False
    assert result["sheets_attempted"] == module.CASCADE_PRIMARY_SHEETS
    assert len(calls) == len(module.CASCADE_PRIMARY_SHEETS)
    for action, _ in calls:
        assert action == "clear_sheet_rows"


def test_run_cascade_delete_participant_include_caches_adds_cache_sheets(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_sheet_admin_actions_module()
    calls: list[tuple[str, dict[str, Any]]] = []

    class _FakeClient:
        def run_admin_action(self, action: str, payload: dict[str, Any]) -> dict[str, Any]:
            calls.append((action, payload))
            return {"status": "success", "dry_run_affected": 0}

    args = Namespace(
        participant_id="p-007",
        execute=False,
        confirm_phrase=None,
        include_caches=True,
    )

    result = module.run_cascade_delete_participant(args, client=_FakeClient())

    expected_sheets = module.CASCADE_PRIMARY_SHEETS + module.CASCADE_CACHE_SHEETS
    assert result["sheets_attempted"] == expected_sheets
    assert result["include_caches"] is True


def test_run_cascade_delete_participant_execute_requires_confirm_phrase() -> None:
    module = _load_sheet_admin_actions_module()

    class _FakeClient:
        def run_admin_action(self, action: str, payload: dict[str, Any]) -> dict[str, Any]:
            return {"status": "success"}

    args = Namespace(
        participant_id="p-042",
        execute=True,
        confirm_phrase=None,
        include_caches=False,
    )

    with pytest.raises(ValueError, match="confirm_phrase inválido"):
        module.run_cascade_delete_participant(args, client=_FakeClient())


def test_run_cascade_delete_participant_stops_on_first_error() -> None:
    module = _load_sheet_admin_actions_module()
    calls: list[str] = []

    class _FlakyClient:
        def run_admin_action(self, action: str, payload: dict[str, Any]) -> dict[str, Any]:
            sheet = payload["target_sheet"]
            calls.append(sheet)
            if sheet == "respuestas":
                raise RuntimeError("timeout")
            return {"status": "success"}

    args = Namespace(
        participant_id="p-fail",
        execute=False,
        confirm_phrase=None,
        include_caches=False,
    )

    result = module.run_cascade_delete_participant(args, client=_FlakyClient())

    # Stops at respuestas (index 1), comment_events ran, rest skipped
    assert calls == ["comment_events", "respuestas"]
    error_result = next(r for r in result["results"] if r["sheet"] == "respuestas")
    assert error_result["status"] == "error"


def test_run_command_cascade_local_only_returns_planned_sheets() -> None:
    module = _load_sheet_admin_actions_module()

    args = Namespace(
        command="cascade-delete-participant",
        no_request=True,
        participant_id="p-999",
        execute=False,
        include_caches=False,
        webapp_url="https://example.test",
        token="tok",
        timeout=10,
    )

    result = module.run_command(args)

    assert result["status"] == "local_only"
    assert result["action"] == "cascade_delete_participant"
    assert result["sheets_planned"] == module.CASCADE_PRIMARY_SHEETS


def test_run_cascade_delete_all_dry_run_calls_all_sheets_with_empty_participant_ids() -> None:
    module = _load_sheet_admin_actions_module()
    calls: list[dict[str, Any]] = []

    class _FakeClient:
        def run_admin_action(self, action: str, payload: dict[str, Any]) -> dict[str, Any]:
            calls.append(payload)
            return {"status": "success", "dry_run_affected": 3}

    args = Namespace(
        execute=False,
        confirm_phrase=None,
        include_caches=False,
    )

    result = module.run_cascade_delete_all(args, client=_FakeClient())

    assert result["scope"] == "all_participants"
    assert result["dry_run"] is True
    assert result["sheets_attempted"] == module.CASCADE_PRIMARY_SHEETS
    for payload in calls:
        assert payload["row_filters"]["participant_ids"] == []


def test_run_cascade_delete_all_execute_requires_correct_confirm_phrase() -> None:
    module = _load_sheet_admin_actions_module()

    class _FakeClient:
        def run_admin_action(self, action: str, payload: dict[str, Any]) -> dict[str, Any]:
            return {"status": "success"}

    args = Namespace(execute=True, confirm_phrase="CASCADE_DELETE_PARTICIPANT", include_caches=False)

    with pytest.raises(ValueError, match="confirm_phrase inválido"):
        module.run_cascade_delete_all(args, client=_FakeClient())


def test_run_command_cascade_delete_all_local_only_shows_scope() -> None:
    module = _load_sheet_admin_actions_module()

    args = Namespace(
        command="cascade-delete-all",
        no_request=True,
        execute=False,
        include_caches=False,
        webapp_url="https://example.test",
        token="tok",
        timeout=10,
    )

    result = module.run_command(args)

    assert result["status"] == "local_only"
    assert result["action"] == "cascade_delete_all"
    assert result["scope"] == "all_participants"
    assert result["sheets_planned"] == module.CASCADE_PRIMARY_SHEETS


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
