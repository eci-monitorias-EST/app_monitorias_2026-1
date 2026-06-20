from __future__ import annotations

from typing import Any

import pytest

from services.configuration import AppConfig
from services.remote_sync import AppsScriptSyncClient


class FakeResponse:
    def __init__(self, payload: dict[str, Any]) -> None:
        self.ok = True
        self.status_code = 200
        self.reason = "OK"
        self.headers = {"Content-Type": "application/json"}
        self._payload = payload

    def json(self) -> dict[str, Any]:
        return self._payload


def test_remote_sync_query_returns_empty_rows_for_malformed_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_post(url: str, *, json: dict[str, Any], timeout: int) -> FakeResponse:
        return FakeResponse({"status": "success", "rows": ["not-a-row"]})

    monkeypatch.setattr(
        "services.remote_sync.load_app_config",
        lambda: AppConfig(raw={"persistence": {"request_timeout_seconds": 9}}),
    )
    monkeypatch.setattr("services.remote_sync.get_script_url", lambda: "https://script")
    monkeypatch.setattr("services.remote_sync.get_form_token", lambda: "token")
    monkeypatch.setattr("services.remote_sync.requests.post", fake_post)

    client = AppsScriptSyncClient()

    assert client.query_comment_events("credit_approval", 10) == []
