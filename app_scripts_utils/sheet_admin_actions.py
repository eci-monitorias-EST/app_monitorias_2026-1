#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any


ROOT_DIR = Path(__file__).resolve().parents[1]
APP_DIR = ROOT_DIR / "app"
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from app_scripts_utils.webapp_client import WebappSyncClient
from config.settings import get_form_token, get_script_url


LOGGER = logging.getLogger(__name__)

DEFAULT_SOURCE_SHEET = "respuestas"
DESTRUCTIVE_CONFIRM_PHRASES = {
    "archive_legacy_rows": "ARCHIVE_LEGACY_ROWS",
    "clear_sheet_rows": "CLEAR_SHEET_ROWS",
    "rebuild_projection_cache": "REBUILD_PROJECTION_CACHE",
}
LEGACY_ROW_FIELDS = {
    "id",
    "ejercicio",
    "comentario",
    "que_parecio",
    "que_hubiera_gustado",
    "cosas_mejorar",
    "feedback_rating",
    "feedback_summary",
    "feedback_missing_topics",
    "feedback_improvement_ideas",
    "selected_exercise",
    "completed_at",
}


def configure_logging() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s - %(message)s")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Opera acciones administrativas seguras del webapp de Google Sheets."
    )
    parser.add_argument("--webapp-url", default=get_script_url(), help="URL del webapp desplegado.")
    parser.add_argument("--token", default=get_form_token(), help="Token compartido con Apps Script.")
    parser.add_argument("--timeout", type=int, default=30, help="Timeout HTTP en segundos.")
    parser.add_argument(
        "--no-request",
        action="store_true",
        help="No invoca el webapp; solo arma y devuelve el payload local.",
    )
    parser.add_argument(
        "--output",
        choices=["json", "pretty"],
        default="pretty",
        help="Formato de salida en consola.",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    fix_parser = subparsers.add_parser(
        "fix-legacy-rows",
        help="Normaliza filas legacy detectadas en respuestas.",
    )
    add_common_legacy_args(fix_parser)
    add_execution_args(fix_parser)

    feedback_parser = subparsers.add_parser(
        "normalize-feedback-schema",
        help="Backfillea feedback canonical a partir de respuestas legacy.",
    )
    add_common_legacy_args(feedback_parser)
    feedback_parser.add_argument("--exercise", help="Filtra por ejercicio específico.")
    add_execution_args(feedback_parser)

    archive_parser = subparsers.add_parser(
        "archive-legacy-rows",
        help="Archiva y opcionalmente elimina filas legacy del sheet fuente.",
    )
    add_common_legacy_args(archive_parser)
    archive_parser.add_argument(
        "--archive-reason",
        default="legacy_snapshot_cleanup",
        help="Motivo de archivo para auditoría.",
    )
    add_execution_args(archive_parser, destructive_action="archive_legacy_rows")

    clear_parser = subparsers.add_parser(
        "clear-sheet-rows",
        help="Limpia filas de una hoja permitida usando filtros explícitos.",
    )
    clear_parser.add_argument("--sheet", required=True, help="Hoja objetivo a limpiar.")
    clear_parser.add_argument(
        "--row-number",
        dest="row_numbers",
        action="append",
        type=int,
        default=[],
        help="Número de fila exacto a borrar. Repetible.",
    )
    clear_parser.add_argument(
        "--participant-id",
        dest="participant_ids",
        action="append",
        default=[],
        help="Filtra por participant_id. Repetible.",
    )
    clear_parser.add_argument("--exercise", help="Filtra por exercise.")
    clear_parser.add_argument("--test-batch-id", help="Filtra por test_batch_id.")
    clear_parser.add_argument("--data-origin", help="Filtra por data_origin.")
    clear_parser.add_argument("--projection-version", help="Filtra por projection_version.")
    clear_parser.add_argument("--embedding-version", help="Filtra por embedding_version.")
    clear_parser.add_argument(
        "--only-legacy",
        action="store_true",
        help="Filtra únicamente filas legacy según heurística del webapp.",
    )
    add_execution_args(clear_parser, destructive_action="clear_sheet_rows")

    embeddings_parser = subparsers.add_parser(
        "backfill-embeddings-cache",
        help="Sube filas explícitas al cache remoto de embeddings.",
    )
    embeddings_parser.add_argument(
        "--rows-file",
        type=Path,
        required=True,
        help="JSON con rows o con {\"rows\": [...]}.",
    )
    embeddings_parser.add_argument("--exercise", required=True, help="Ejercicio de las filas.")
    embeddings_parser.add_argument(
        "--embedding-version",
        required=True,
        help="Versión explícita del embedding cache.",
    )
    embeddings_parser.add_argument(
        "--embedding-provider",
        required=True,
        help="Proveedor explícito del embedding cache.",
    )
    add_execution_args(embeddings_parser)

    projection_parser = subparsers.add_parser(
        "rebuild-projection-cache",
        help="Reconstruye una versión explícita de projection_cache.",
    )
    projection_parser.add_argument(
        "--rows-file",
        type=Path,
        required=True,
        help="JSON con rows o con {\"rows\": [...]}.",
    )
    projection_parser.add_argument("--exercise", required=True, help="Ejercicio objetivo.")
    projection_parser.add_argument(
        "--projection-version",
        required=True,
        help="Versión explícita a reconstruir en cache.",
    )
    projection_parser.add_argument(
        "--embedding-provider",
        default="",
        help="Proveedor de embeddings asociado a la proyección.",
    )
    projection_parser.add_argument(
        "--reduction-provider",
        default="",
        help="Proveedor de reducción asociado a la proyección.",
    )
    projection_parser.add_argument(
        "--append-only",
        action="store_true",
        help="No reemplaza el scope previo; solo hace upsert por clave.",
    )
    add_execution_args(projection_parser, destructive_action="rebuild_projection_cache")

    return parser


def add_common_legacy_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--source-sheet",
        default=DEFAULT_SOURCE_SHEET,
        help="Hoja fuente consolidada. Por defecto respuestas.",
    )
    parser.add_argument(
        "--snapshot",
        type=Path,
        help="Manifest o snapshot exportado para detectar filas legacy automáticamente.",
    )
    parser.add_argument(
        "--selector-file",
        type=Path,
        help="JSON con legacy_row_selectors prearmados.",
    )
    parser.add_argument(
        "--row-number",
        dest="row_numbers",
        action="append",
        type=int,
        default=[],
        help="Número de fila exacto a operar. Repetible.",
    )
    parser.add_argument(
        "--participant-id",
        dest="participant_ids",
        action="append",
        default=[],
        help="participant_id puntual a incluir como selector. Repetible.",
    )
    parser.add_argument(
        "--selector-exercise",
        dest="selector_exercise",
        help="exercise a incluir en los selectores directos.",
    )


def add_execution_args(
    parser: argparse.ArgumentParser,
    *,
    destructive_action: str | None = None,
) -> None:
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Ejecuta escrituras reales. Sin este flag el payload va con dry_run=true.",
    )
    if destructive_action:
        parser.add_argument(
            "--confirm-phrase",
            help=(
                "Confirmación explícita requerida para la ejecución real. "
                f"Esperado: {DESTRUCTIVE_CONFIRM_PHRASES[destructive_action]}"
            ),
        )


def create_client(args: argparse.Namespace) -> WebappSyncClient:
    return WebappSyncClient(url=args.webapp_url, token=args.token, timeout=args.timeout)


def load_json_file(file_path: Path) -> Any:
    return json.loads(file_path.read_text(encoding="utf-8"))


def load_rows_payload(file_path: Path) -> list[dict[str, Any]]:
    payload = load_json_file(file_path)
    if isinstance(payload, list):
        rows = payload
    elif isinstance(payload, dict) and isinstance(payload.get("rows"), list):
        rows = payload["rows"]
    else:
        raise ValueError("rows-file debe contener una lista o un objeto con clave rows.")

    normalized_rows: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("Cada row del rows-file debe ser un objeto JSON.")
        normalized_rows.append(dict(row))
    return normalized_rows


def build_legacy_row_selectors_from_snapshot(
    snapshot_payload: dict[str, Any],
    *,
    source_sheet: str,
) -> list[dict[str, Any]]:
    sheet_payload = extract_snapshot_sheet_payload(snapshot_payload, source_sheet=source_sheet)
    selectors: list[dict[str, Any]] = []
    for row in sheet_payload.get("rows", []):
        if not isinstance(row, dict):
            continue
        legacy_fields = sorted(detect_legacy_fields(row))
        if not legacy_fields:
            continue
        selector: dict[str, Any] = {"legacy_fields": legacy_fields}
        row_number = row.get("_sheet_row_number")
        if row_number not in (None, ""):
            selector["row_number"] = int(row_number)
        for field in ("participant_id", "exercise", "test_batch_id", "data_origin"):
            value = str(row.get(field, "")).strip()
            if value:
                selector[field] = value
        selectors.append(selector)
    return deduplicate_selectors(selectors)


def extract_snapshot_sheet_payload(
    snapshot_payload: dict[str, Any],
    *,
    source_sheet: str,
) -> dict[str, Any]:
    if isinstance(snapshot_payload.get("sheets"), dict):
        return dict(snapshot_payload["sheets"].get(source_sheet, {}))
    return dict(snapshot_payload)


def detect_legacy_fields(row: dict[str, Any]) -> set[str]:
    return {
        field_name
        for field_name in row
        if field_name in LEGACY_ROW_FIELDS and str(row.get(field_name, "")).strip()
    }


def deduplicate_selectors(selectors: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    seen: set[str] = set()
    for selector in selectors:
        serialized = json.dumps(selector, sort_keys=True, ensure_ascii=False)
        if serialized in seen:
            continue
        normalized.append(selector)
        seen.add(serialized)
    return normalized


def build_direct_selectors(args: argparse.Namespace) -> list[dict[str, Any]]:
    selectors: list[dict[str, Any]] = []
    normalized_exercise = str(getattr(args, "selector_exercise", "") or "").strip()
    for row_number in getattr(args, "row_numbers", []):
        selector: dict[str, Any] = {"row_number": int(row_number)}
        if normalized_exercise:
            selector["exercise"] = normalized_exercise
        selectors.append(selector)
    for participant_id in getattr(args, "participant_ids", []):
        selector = {"participant_id": str(participant_id).strip()}
        if normalized_exercise:
            selector["exercise"] = normalized_exercise
        selectors.append(selector)
    return [selector for selector in selectors if any(selector.values())]


def build_legacy_selectors(args: argparse.Namespace) -> list[dict[str, Any]]:
    selectors: list[dict[str, Any]] = []
    source_sheet = str(args.source_sheet).strip() or DEFAULT_SOURCE_SHEET
    if getattr(args, "snapshot", None):
        snapshot_payload = load_json_file(args.snapshot)
        selectors.extend(
            build_legacy_row_selectors_from_snapshot(snapshot_payload, source_sheet=source_sheet)
        )
    if getattr(args, "selector_file", None):
        raw_payload = load_json_file(args.selector_file)
        if not isinstance(raw_payload, list):
            raise ValueError("selector-file debe contener una lista de selectores.")
        selectors.extend([dict(item) for item in raw_payload])
    selectors.extend(build_direct_selectors(args))
    return deduplicate_selectors(selectors)


def maybe_add_confirm_phrase(
    payload: dict[str, Any],
    *,
    action: str,
    execute: bool,
    confirm_phrase: str | None,
    required: bool,
) -> dict[str, Any]:
    if not execute:
        return payload
    if required:
        expected = DESTRUCTIVE_CONFIRM_PHRASES[action]
        if confirm_phrase != expected:
            raise ValueError(
                f"confirm_phrase inválido para {action}. Esperado: {expected}"
            )
    if confirm_phrase:
        payload["confirm_phrase"] = confirm_phrase
    return payload


def build_fix_legacy_rows_payload(args: argparse.Namespace) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "source_sheet": str(args.source_sheet).strip() or DEFAULT_SOURCE_SHEET,
        "dry_run": not args.execute,
    }
    selectors = build_legacy_selectors(args)
    if selectors:
        payload["legacy_row_selectors"] = selectors
    return payload


def build_normalize_feedback_schema_payload(args: argparse.Namespace) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "source_sheet": str(args.source_sheet).strip() or DEFAULT_SOURCE_SHEET,
        "dry_run": not args.execute,
    }
    selectors = build_legacy_selectors(args)
    if selectors:
        payload["legacy_row_selectors"] = selectors
    exercise = str(getattr(args, "exercise", "") or "").strip()
    if exercise:
        payload["exercise"] = exercise
    return payload


def build_archive_legacy_rows_payload(args: argparse.Namespace) -> dict[str, Any]:
    payload = {
        "source_sheet": str(args.source_sheet).strip() or DEFAULT_SOURCE_SHEET,
        "archive_reason": str(args.archive_reason).strip(),
        "dry_run": not args.execute,
    }
    selectors = build_legacy_selectors(args)
    if selectors:
        payload["legacy_row_selectors"] = selectors
    return maybe_add_confirm_phrase(
        payload,
        action="archive_legacy_rows",
        execute=args.execute,
        confirm_phrase=getattr(args, "confirm_phrase", None),
        required=True,
    )


def build_clear_sheet_rows_payload(args: argparse.Namespace) -> dict[str, Any]:
    row_filters = {
        "row_numbers": [int(value) for value in args.row_numbers],
        "participant_ids": [str(value).strip() for value in args.participant_ids if str(value).strip()],
        "exercise": str(args.exercise or "").strip(),
        "test_batch_id": str(args.test_batch_id or "").strip(),
        "data_origin": str(args.data_origin or "").strip(),
        "projection_version": str(args.projection_version or "").strip(),
        "embedding_version": str(args.embedding_version or "").strip(),
        "only_legacy": bool(args.only_legacy),
    }
    payload: dict[str, Any] = {
        "target_sheet": str(args.sheet).strip(),
        "dry_run": not args.execute,
        "row_filters": row_filters,
    }
    return maybe_add_confirm_phrase(
        payload,
        action="clear_sheet_rows",
        execute=args.execute,
        confirm_phrase=getattr(args, "confirm_phrase", None),
        required=True,
    )


def build_backfill_embeddings_cache_payload(args: argparse.Namespace) -> dict[str, Any]:
    rows = []
    for row in load_rows_payload(args.rows_file):
        participant_id = str(row.get("participant_id", "")).strip()
        if not participant_id:
            raise ValueError("Cada fila de embeddings_cache requiere participant_id.")
        normalized_row = dict(row)
        normalized_row["participant_id"] = participant_id
        normalized_row["exercise"] = str(row.get("exercise") or args.exercise).strip()
        normalized_row["embedding_version"] = str(
            row.get("embedding_version") or args.embedding_version
        ).strip()
        normalized_row["embedding_provider"] = str(
            row.get("embedding_provider") or args.embedding_provider
        ).strip()
        rows.append(normalized_row)
    return {
        "dry_run": not args.execute,
        "rows": rows,
    }


def build_rebuild_projection_cache_payload(args: argparse.Namespace) -> dict[str, Any]:
    rows = []
    for row in load_rows_payload(args.rows_file):
        participant_id = str(row.get("participant_id", "")).strip()
        if not participant_id:
            raise ValueError("Cada fila de projection_cache requiere participant_id.")
        normalized_row = dict(row)
        normalized_row["participant_id"] = participant_id
        normalized_row["exercise"] = str(row.get("exercise") or args.exercise).strip()
        normalized_row["projection_version"] = str(
            row.get("projection_version") or args.projection_version
        ).strip()
        if args.embedding_provider:
            normalized_row.setdefault("embedding_provider", str(args.embedding_provider).strip())
        if args.reduction_provider:
            normalized_row.setdefault("reduction_provider", str(args.reduction_provider).strip())
        rows.append(normalized_row)

    replace_existing_scope = not args.append_only
    payload: dict[str, Any] = {
        "exercise": str(args.exercise).strip(),
        "projection_version": str(args.projection_version).strip(),
        "dry_run": not args.execute,
        "replace_existing_scope": replace_existing_scope,
        "rows": rows,
    }
    return maybe_add_confirm_phrase(
        payload,
        action="rebuild_projection_cache",
        execute=args.execute,
        confirm_phrase=getattr(args, "confirm_phrase", None),
        required=replace_existing_scope,
    )


def build_action_request(args: argparse.Namespace) -> tuple[str, dict[str, Any]]:
    if args.command == "fix-legacy-rows":
        return "fix_legacy_rows", build_fix_legacy_rows_payload(args)
    if args.command == "normalize-feedback-schema":
        return "normalize_feedback_schema", build_normalize_feedback_schema_payload(args)
    if args.command == "archive-legacy-rows":
        return "archive_legacy_rows", build_archive_legacy_rows_payload(args)
    if args.command == "clear-sheet-rows":
        return "clear_sheet_rows", build_clear_sheet_rows_payload(args)
    if args.command == "backfill-embeddings-cache":
        return "backfill_embeddings_cache", build_backfill_embeddings_cache_payload(args)
    if args.command == "rebuild-projection-cache":
        return "rebuild_projection_cache", build_rebuild_projection_cache_payload(args)
    raise ValueError(f"Comando no soportado: {args.command}")


def render_output(payload: dict[str, Any], *, output_format: str) -> str:
    if output_format == "json":
        return json.dumps(payload, ensure_ascii=False)
    return json.dumps(payload, ensure_ascii=False, indent=2)


def run_command(
    args: argparse.Namespace,
    *,
    client: WebappSyncClient | None = None,
) -> dict[str, Any]:
    action, payload = build_action_request(args)
    if args.no_request:
        return {
            "status": "local_only",
            "action": action,
            "payload": payload,
        }

    effective_client = client or create_client(args)
    response = effective_client.run_admin_action(action, payload)
    return {
        "status": "success",
        "action": action,
        "request_payload": payload,
        "response": response,
    }


def main() -> int:
    configure_logging()
    parser = build_parser()
    args = parser.parse_args()

    try:
        result = run_command(args)
    except Exception:
        LOGGER.exception("Falló la operación administrativa remota de Google Sheets.")
        return 1

    print(render_output(result, output_format=args.output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
