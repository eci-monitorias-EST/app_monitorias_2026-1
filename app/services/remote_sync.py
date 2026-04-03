from __future__ import annotations

import logging
from typing import Any

import requests

from config.settings import get_form_token, get_script_url
from services.configuration import load_app_config


LOGGER = logging.getLogger(__name__)


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

    def _get_missing_configuration_fields(self) -> tuple[str, ...]:
        missing_fields: list[str] = []
        if not self.url:
            missing_fields.append("url")
        if not self.token:
            missing_fields.append("token")
        return tuple(missing_fields)

    def _post(self, action: str, payload: dict[str, Any]) -> None:
        missing_fields = self._get_missing_configuration_fields()
        if missing_fields:
            LOGGER.warning(
                "Skipping remote sync due to missing configuration.",
                extra={"action": action, "missing_fields": missing_fields},
            )
            return

        try:
            response = requests.post(
                self.url,
                json={"token": self.token, "accion": action, **payload},
                timeout=self.timeout,
            )
        except requests.RequestException:
            LOGGER.warning(
                "Remote sync request failed; continuing with local-first flow.",
                exc_info=True,
                extra={"action": action, "timeout_seconds": self.timeout},
            )
            return

        if not response.ok:
            LOGGER.warning(
                "Remote sync returned a non-success response; continuing with local-first flow.",
                extra={
                    "action": action,
                    "status_code": response.status_code,
                    "reason": response.reason,
                },
            )
            return

        LOGGER.info(
            "Remote sync completed successfully.",
            extra={"action": action, "status_code": response.status_code},
        )

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
