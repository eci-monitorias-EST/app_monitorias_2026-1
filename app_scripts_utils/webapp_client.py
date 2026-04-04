from __future__ import annotations

from typing import Any

import requests


class WebappSyncClient:
    def __init__(self, *, url: str, token: str, timeout: int) -> None:
        self.url = url.strip()
        self.token = token.strip()
        self.timeout = timeout

    def build_payload(self, action: str, payload: dict[str, Any]) -> dict[str, Any]:
        return {"token": self.token, "accion": action, **payload}

    def post(self, action: str, payload: dict[str, Any]) -> dict[str, Any]:
        if not self.url:
            raise ValueError("Falta GOOGLE_SCRIPT_URL o --webapp-url.")
        if not self.token:
            raise ValueError("Falta GOOGLE_SCRIPT_TOKEN o --token.")

        response = requests.post(
            self.url,
            json=self.build_payload(action, payload),
            timeout=self.timeout,
        )
        response.raise_for_status()
        data = response.json()
        if data.get("status") != "success":
            raise RuntimeError(
                f"El webapp devolvió error para {action}: {data.get('message', 'sin detalle')}"
            )
        return data

    def run_admin_action(self, action: str, payload: dict[str, Any]) -> dict[str, Any]:
        return self.post(action, payload)

    def export_sheet_snapshot(
        self,
        *,
        sheet_names: list[str],
        limit_rows: int,
    ) -> dict[str, Any]:
        return self.post(
            "export_sheet_snapshot",
            {
                "sheet_names": sheet_names,
                "limit_rows": limit_rows,
            },
        )

    def fix_legacy_rows(
        self,
        *,
        source_sheet: str,
        dry_run: bool,
        legacy_row_selectors: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "source_sheet": source_sheet,
            "dry_run": dry_run,
        }
        if legacy_row_selectors:
            payload["legacy_row_selectors"] = legacy_row_selectors
        return self.run_admin_action("fix_legacy_rows", payload)

    def normalize_feedback_schema(
        self,
        *,
        source_sheet: str,
        dry_run: bool,
        legacy_row_selectors: list[dict[str, Any]] | None = None,
        exercise: str | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "source_sheet": source_sheet,
            "dry_run": dry_run,
        }
        if legacy_row_selectors:
            payload["legacy_row_selectors"] = legacy_row_selectors
        if exercise:
            payload["exercise"] = exercise
        return self.run_admin_action("normalize_feedback_schema", payload)

    def archive_legacy_rows(
        self,
        *,
        source_sheet: str,
        dry_run: bool,
        confirm_phrase: str | None = None,
        legacy_row_selectors: list[dict[str, Any]] | None = None,
        archive_reason: str | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "source_sheet": source_sheet,
            "dry_run": dry_run,
        }
        if confirm_phrase:
            payload["confirm_phrase"] = confirm_phrase
        if legacy_row_selectors:
            payload["legacy_row_selectors"] = legacy_row_selectors
        if archive_reason:
            payload["archive_reason"] = archive_reason
        return self.run_admin_action("archive_legacy_rows", payload)

    def clear_sheet_rows(
        self,
        *,
        target_sheet: str,
        dry_run: bool,
        row_filters: dict[str, Any],
        confirm_phrase: str | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "target_sheet": target_sheet,
            "dry_run": dry_run,
            "row_filters": row_filters,
        }
        if confirm_phrase:
            payload["confirm_phrase"] = confirm_phrase
        return self.run_admin_action("clear_sheet_rows", payload)

    def backfill_embeddings_cache(
        self,
        *,
        dry_run: bool,
        rows: list[dict[str, Any]],
    ) -> dict[str, Any]:
        return self.run_admin_action(
            "backfill_embeddings_cache",
            {
                "dry_run": dry_run,
                "rows": rows,
            },
        )

    def query_projection_comments(self, *, exercise: str, limit_rows: int = 500) -> dict[str, Any]:
        return self.post(
            "query_projection_comments",
            {"exercise": exercise, "limit_rows": limit_rows},
        )

    def query_embeddings_cache(
        self,
        *,
        exercise: str,
        embedding_version: str,
        participant_ids: list[str] | None = None,
        comment_hashes: list[str] | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "exercise": exercise,
            "embedding_version": embedding_version,
        }
        if participant_ids:
            payload["participant_ids"] = participant_ids
        if comment_hashes:
            payload["comment_hashes"] = comment_hashes
        return self.post("query_embeddings_cache", payload)

    def upsert_embeddings_cache(self, *, rows: list[dict[str, Any]]) -> dict[str, Any]:
        return self.post("upsert_embeddings_cache", {"rows": rows})

    def query_projection_cache(
        self,
        *,
        exercise: str,
        projection_version: str,
        participant_ids: list[str] | None = None,
        comment_hashes: list[str] | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "exercise": exercise,
            "projection_version": projection_version,
        }
        if participant_ids:
            payload["participant_ids"] = participant_ids
        if comment_hashes:
            payload["comment_hashes"] = comment_hashes
        return self.post("query_projection_cache", payload)

    def upsert_projection_cache(self, *, rows: list[dict[str, Any]]) -> dict[str, Any]:
        return self.post("upsert_projection_cache", {"rows": rows})

    def rebuild_projection_cache(
        self,
        *,
        exercise: str,
        projection_version: str,
        dry_run: bool,
        rows: list[dict[str, Any]],
        replace_existing_scope: bool,
        confirm_phrase: str | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "exercise": exercise,
            "projection_version": projection_version,
            "dry_run": dry_run,
            "rows": rows,
            "replace_existing_scope": replace_existing_scope,
        }
        if confirm_phrase:
            payload["confirm_phrase"] = confirm_phrase
        return self.run_admin_action("rebuild_projection_cache", payload)
