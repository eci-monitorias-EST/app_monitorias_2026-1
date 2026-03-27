from __future__ import annotations

from typing import Any

import requests

from config.settings import get_form_token, get_script_url
from services.configuration import load_app_config


class RemoteSyncClient:
    def sync_participant(self, participant_payload: dict[str, Any]) -> None:
        return None

    def sync_progress(self, progress_payload: dict[str, Any]) -> None:
        return None

    def sync_feedback(self, feedback_payload: dict[str, Any]) -> None:
        return None

    def sync_completion(self, completion_payload: dict[str, Any]) -> None:
        return None


class NoopRemoteSyncClient(RemoteSyncClient):
    pass


class AppsScriptSyncClient(RemoteSyncClient):
    def __init__(self) -> None:
        config = load_app_config()
        self.timeout = int(config.persistence.get("request_timeout_seconds", 10))
        self.url = get_script_url()
        self.token = get_form_token()

    def _post(self, action: str, payload: dict[str, Any]) -> None:
        if not self.url or not self.token:
            return
        try:
            requests.post(
                self.url,
                json={"token": self.token, "accion": action, **payload},
                timeout=self.timeout,
            )
        except requests.RequestException:
            return

    def sync_participant(self, participant_payload: dict[str, Any]) -> None:
        self._post("upsert_sesion", participant_payload)

    def sync_progress(self, progress_payload: dict[str, Any]) -> None:
        self._post("upsert_respuesta", progress_payload)

    def sync_feedback(self, feedback_payload: dict[str, Any]) -> None:
        self._post("upsert_feedback", feedback_payload)

    def sync_completion(self, completion_payload: dict[str, Any]) -> None:
        self._post("marcar_completado", completion_payload)


def build_remote_sync_client() -> RemoteSyncClient:
    config = load_app_config()
    if config.persistence.get("sync_to_apps_script"):
        return AppsScriptSyncClient()
    return NoopRemoteSyncClient()
