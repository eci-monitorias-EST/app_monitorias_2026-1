from __future__ import annotations

import logging
from typing import Any

import pytest
import requests

from services.configuration import AppConfig
from services.remote_sync import (
    AppsScriptSyncClient,
    NoopRemoteSyncClient,
    build_remote_sync_client,
)


class FakeResponse:
    def __init__(
        self,
        *,
        ok: bool,
        status_code: int,
        reason: str,
        payload: dict[str, Any] | None = None,
        json_error: Exception | None = None,
        content_type: str = "application/json",
    ) -> None:
        self.ok = ok
        self.status_code = status_code
        self.reason = reason
        self._payload = payload or {"status": "success", "mode": "insert"}
        self._json_error = json_error
        self.headers = {"Content-Type": content_type}

    def json(self) -> dict[str, Any]:
        if self._json_error is not None:
            raise self._json_error
        return self._payload


def test_build_remote_sync_client_returns_apps_script_client_when_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "services.remote_sync.load_app_config",
        lambda: AppConfig(
            raw={"persistence": {"sync_to_apps_script": True, "request_timeout_seconds": 17}}
        ),
    )
    monkeypatch.setattr("services.remote_sync.get_script_url", lambda: "https://script.google.test")
    monkeypatch.setattr("services.remote_sync.get_form_token", lambda: "secret-token")

    client = build_remote_sync_client()

    assert isinstance(client, AppsScriptSyncClient)
    assert client.timeout == 17
    assert client.url == "https://script.google.test"
    assert client.token == "secret-token"


def test_build_remote_sync_client_returns_noop_when_sync_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "services.remote_sync.load_app_config",
        lambda: AppConfig(raw={"persistence": {"sync_to_apps_script": False}}),
    )

    client = build_remote_sync_client()

    assert isinstance(client, NoopRemoteSyncClient)


@pytest.mark.parametrize(
    ("method_name", "action", "payload"),
    [
        ("sync_participant", "upsert_sesion", {"participant_id": "p-001"}),
        (
            "sync_progress",
            "upsert_respuesta",
            {"participant_id": "p-001", "exercise": "credit_approval", "payload": {"step": 1}},
        ),
        (
            "sync_feedback",
            "upsert_feedback",
            {"participant_id": "p-001", "exercise": "credit_approval", "payload": {"rating": 5}},
        ),
        (
            "sync_comment_events",
            "upsert_comment_events",
            {"participant_id": "p-001", "exercise": "credit_approval", "rows": [{"comment_hash": "h1"}]},
        ),
        (
            "sync_completion",
            "marcar_completado",
            {"participant_id": "p-001", "exercise": "credit_approval"},
        ),
    ],
)
def test_apps_script_client_posts_expected_action_and_payload(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    method_name: str,
    action: str,
    payload: dict[str, Any],
) -> None:
    captured_request: dict[str, Any] = {}

    def fake_post(url: str, *, json: dict[str, Any], timeout: int) -> FakeResponse:
        captured_request["url"] = url
        captured_request["json"] = json
        captured_request["timeout"] = timeout
        return FakeResponse(ok=True, status_code=200, reason="OK")

    monkeypatch.setattr(
        "services.remote_sync.load_app_config",
        lambda: AppConfig(raw={"persistence": {"request_timeout_seconds": 9}}),
    )
    monkeypatch.setattr("services.remote_sync.get_script_url", lambda: "https://script.google.test")
    monkeypatch.setattr("services.remote_sync.get_form_token", lambda: "form-token")
    monkeypatch.setattr("services.remote_sync.requests.post", fake_post)

    client = AppsScriptSyncClient()
    caplog.set_level(logging.INFO, logger="services.remote_sync")

    sync_method = getattr(client, method_name)
    sync_method(payload)

    assert captured_request == {
        "url": "https://script.google.test",
        "json": {"token": "form-token", "accion": action, **payload},
        "timeout": 9,
    }
    assert "Remote sync completed successfully." in caplog.text


@pytest.mark.parametrize(
    ("method_name", "expected_action", "payload", "expected_rows"),
    [
        (
            "query_comment_events",
            "query_comment_events",
            {"exercise": "credit_approval", "limit_rows": 200},
            [{"participant_id": "p-001", "comment_hash": "hash-1"}],
        ),
        (
            "query_projection_comments",
            "query_projection_comments",
            {"exercise": "credit_approval", "limit_rows": 200},
            [{"participant_id": "p-001", "combined_comment": "comentario legado"}],
        ),
        (
            "query_embeddings_cache",
            "query_embeddings_cache",
            {
                "exercise": "credit_approval",
                "embedding_version": "emb-v1",
                "comment_hashes": ["hash-1"],
            },
            [{"participant_id": "p-001", "comment_hash": "hash-1"}],
        ),
        (
            "query_projection_cache",
            "query_projection_cache",
            {
                "exercise": "credit_approval",
                "projection_version": "proj-v1",
                "comment_hashes": ["hash-1"],
            },
            [{"participant_id": "p-001", "comment_hash": "hash-1"}],
        ),
    ],
)
def test_apps_script_client_queries_cache_payloads(
    monkeypatch: pytest.MonkeyPatch,
    method_name: str,
    expected_action: str,
    payload: dict[str, Any],
    expected_rows: list[dict[str, Any]],
) -> None:
    captured_request: dict[str, Any] = {}

    def fake_post(url: str, *, json: dict[str, Any], timeout: int) -> FakeResponse:
        captured_request["url"] = url
        captured_request["json"] = json
        captured_request["timeout"] = timeout
        return FakeResponse(ok=True, status_code=200, reason="OK", payload={"status": "success", "rows": expected_rows})

    monkeypatch.setattr(
        "services.remote_sync.load_app_config",
        lambda: AppConfig(raw={"persistence": {"request_timeout_seconds": 9}}),
    )
    monkeypatch.setattr("services.remote_sync.get_script_url", lambda: "https://script.google.test")
    monkeypatch.setattr("services.remote_sync.get_form_token", lambda: "form-token")
    monkeypatch.setattr("services.remote_sync.requests.post", fake_post)

    client = AppsScriptSyncClient()
    result = getattr(client, method_name)(**payload)

    assert result == expected_rows
    assert captured_request == {
        "url": "https://script.google.test",
        "json": {"token": "form-token", "accion": expected_action, **payload},
        "timeout": 9,
    }


@pytest.mark.parametrize(
    ("method_name", "payload", "expected_action"),
    [
        ("upsert_embeddings_cache", {"rows": [{"participant_id": "p-001", "comment_hash": "h1"}]}, "upsert_embeddings_cache"),
        ("upsert_projection_cache", {"rows": [{"participant_id": "p-001", "comment_hash": "h1"}]}, "upsert_projection_cache"),
    ],
)
def test_apps_script_client_upserts_cache_payloads(
    monkeypatch: pytest.MonkeyPatch,
    method_name: str,
    payload: dict[str, Any],
    expected_action: str,
) -> None:
    captured_request: dict[str, Any] = {}

    def fake_post(url: str, *, json: dict[str, Any], timeout: int) -> FakeResponse:
        captured_request["url"] = url
        captured_request["json"] = json
        captured_request["timeout"] = timeout
        return FakeResponse(ok=True, status_code=200, reason="OK")

    monkeypatch.setattr(
        "services.remote_sync.load_app_config",
        lambda: AppConfig(raw={"persistence": {"request_timeout_seconds": 9}}),
    )
    monkeypatch.setattr("services.remote_sync.get_script_url", lambda: "https://script.google.test")
    monkeypatch.setattr("services.remote_sync.get_form_token", lambda: "form-token")
    monkeypatch.setattr("services.remote_sync.requests.post", fake_post)

    client = AppsScriptSyncClient()
    getattr(client, method_name)(**payload)

    assert captured_request == {
        "url": "https://script.google.test",
        "json": {"token": "form-token", "accion": expected_action, **payload},
        "timeout": 9,
    }


def test_apps_script_client_logs_warning_when_response_is_not_json(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    def fake_post(*args: Any, **kwargs: Any) -> FakeResponse:
        return FakeResponse(
            ok=True,
            status_code=200,
            reason="OK",
            json_error=ValueError("invalid json"),
            content_type="text/html",
        )

    monkeypatch.setattr(
        "services.remote_sync.load_app_config",
        lambda: AppConfig(raw={"persistence": {"request_timeout_seconds": 5}}),
    )
    monkeypatch.setattr("services.remote_sync.get_script_url", lambda: "https://script.google.test")
    monkeypatch.setattr("services.remote_sync.get_form_token", lambda: "form-token")
    monkeypatch.setattr("services.remote_sync.requests.post", fake_post)

    client = AppsScriptSyncClient()
    caplog.set_level(logging.WARNING, logger="services.remote_sync")

    client.sync_progress({"participant_id": "p-001", "exercise": "credit_approval", "payload": {}})

    assert "Remote sync returned a non-JSON response" in caplog.text
    assert any(record.content_type == "text/html" for record in caplog.records)


def test_apps_script_client_logs_warning_when_response_payload_reports_error(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    def fake_post(*args: Any, **kwargs: Any) -> FakeResponse:
        return FakeResponse(
            ok=True,
            status_code=200,
            reason="OK",
            payload={"status": "error", "message": "No autorizado"},
        )

    monkeypatch.setattr(
        "services.remote_sync.load_app_config",
        lambda: AppConfig(raw={"persistence": {"request_timeout_seconds": 5}}),
    )
    monkeypatch.setattr("services.remote_sync.get_script_url", lambda: "https://script.google.test")
    monkeypatch.setattr("services.remote_sync.get_form_token", lambda: "form-token")
    monkeypatch.setattr("services.remote_sync.requests.post", fake_post)

    client = AppsScriptSyncClient()
    caplog.set_level(logging.WARNING, logger="services.remote_sync")

    client.sync_participant({"participant_id": "p-001"})

    assert "Remote sync returned an application-level error" in caplog.text
    assert any(record.remote_status == "error" for record in caplog.records)
    assert any(record.remote_message == "No autorizado" for record in caplog.records)


@pytest.mark.parametrize(
    ("status_code", "reason"),
    [
        (400, "Bad Request"),
        (500, "Internal Server Error"),
    ],
)
def test_apps_script_client_logs_warning_when_response_is_not_ok(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    status_code: int,
    reason: str,
) -> None:
    def fake_post(*args: Any, **kwargs: Any) -> FakeResponse:
        return FakeResponse(ok=False, status_code=status_code, reason=reason)

    monkeypatch.setattr(
        "services.remote_sync.load_app_config",
        lambda: AppConfig(raw={"persistence": {"request_timeout_seconds": 5}}),
    )
    monkeypatch.setattr("services.remote_sync.get_script_url", lambda: "https://script.google.test")
    monkeypatch.setattr("services.remote_sync.get_form_token", lambda: "form-token")
    monkeypatch.setattr("services.remote_sync.requests.post", fake_post)

    client = AppsScriptSyncClient()
    caplog.set_level(logging.WARNING, logger="services.remote_sync")

    client.sync_feedback({"participant_id": "p-001", "payload": {"rating": 4}})

    assert "Remote sync returned a non-success response" in caplog.text
    assert any(record.status_code == status_code for record in caplog.records)
    assert any(record.reason == reason for record in caplog.records)


@pytest.mark.parametrize(
    ("url", "token", "missing_fields"),
    [
        ("", "form-token", ("url",)),
        ("https://script.google.test", "", ("token",)),
        ("", "", ("url", "token")),
    ],
)
def test_apps_script_client_is_noop_when_configuration_is_missing(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    url: str,
    token: str,
    missing_fields: tuple[str, ...],
) -> None:
    post_called = False

    def fake_post(*args: Any, **kwargs: Any) -> None:
        nonlocal post_called
        post_called = True

    monkeypatch.setattr(
        "services.remote_sync.load_app_config",
        lambda: AppConfig(raw={"persistence": {"request_timeout_seconds": 5}}),
    )
    monkeypatch.setattr("services.remote_sync.get_script_url", lambda: url)
    monkeypatch.setattr("services.remote_sync.get_form_token", lambda: token)
    monkeypatch.setattr("services.remote_sync.requests.post", fake_post)

    client = AppsScriptSyncClient()
    caplog.set_level(logging.WARNING, logger="services.remote_sync")

    client.sync_progress({"participant_id": "p-001", "payload": {"step": 1}})

    assert post_called is False
    assert "Skipping remote sync due to missing configuration." in caplog.text
    assert any(record.missing_fields == missing_fields for record in caplog.records)


def test_apps_script_client_swallows_request_exception(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    def fake_post(*args: Any, **kwargs: Any) -> None:
        raise requests.RequestException("network down")

    monkeypatch.setattr(
        "services.remote_sync.load_app_config",
        lambda: AppConfig(raw={"persistence": {"request_timeout_seconds": 5}}),
    )
    monkeypatch.setattr("services.remote_sync.get_script_url", lambda: "https://script.google.test")
    monkeypatch.setattr("services.remote_sync.get_form_token", lambda: "form-token")
    monkeypatch.setattr("services.remote_sync.requests.post", fake_post)

    client = AppsScriptSyncClient()
    caplog.set_level(logging.WARNING, logger="services.remote_sync")

    client.sync_feedback({"participant_id": "p-001", "payload": {"rating": 4}})

    assert "Remote sync request failed; continuing with local-first flow." in caplog.text
    assert any(record.action == "upsert_feedback" for record in caplog.records)
