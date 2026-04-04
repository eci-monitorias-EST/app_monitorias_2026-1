#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import logging
import sys
from datetime import datetime, timezone
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
DEFAULT_OUTPUT_DIR = ROOT_DIR / "data" / "processed" / "sheet_snapshots"
DEFAULT_LIMIT_ROWS = 200
MAX_LIMIT_ROWS = 500


def configure_logging() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s - %(message)s")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Exporta snapshots controlados de hojas Google Sheet vía Apps Script."
    )
    parser.add_argument("--webapp-url", default=get_script_url(), help="URL del webapp desplegado.")
    parser.add_argument("--token", default=get_form_token(), help="Token compartido con Apps Script.")
    parser.add_argument("--timeout", type=int, default=30, help="Timeout HTTP en segundos.")
    parser.add_argument(
        "--sheet",
        dest="sheets",
        action="append",
        default=[],
        help="Nombre de hoja exportable. Repetir el flag para varias hojas.",
    )
    parser.add_argument(
        "--limit-rows",
        type=int,
        default=DEFAULT_LIMIT_ROWS,
        help=f"Máximo de filas por hoja. Máximo permitido: {MAX_LIMIT_ROWS}.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directorio local donde se guardan JSON/CSV.",
    )
    parser.add_argument(
        "--format",
        choices=["json", "csv", "both"],
        default="both",
        help="Formato de exportación local.",
    )
    parser.add_argument(
        "--snapshot-label",
        default=build_default_snapshot_label(),
        help="Etiqueta para agrupar archivos locales.",
    )
    return parser


def build_default_snapshot_label() -> str:
    return datetime.now(timezone.utc).strftime("sheet-snapshot-%Y%m%d-%H%M%S")


def normalize_sheet_names(sheet_names: list[str]) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for raw_name in sheet_names:
        name = str(raw_name).strip()
        if not name or name in seen:
            continue
        normalized.append(name)
        seen.add(name)
    if not normalized:
        raise ValueError("Debés indicar al menos una hoja con --sheet.")
    return normalized


def normalize_limit_rows(limit_rows: int) -> int:
    if limit_rows <= 0:
        raise ValueError("limit_rows debe ser mayor que cero.")
    return min(limit_rows, MAX_LIMIT_ROWS)


def create_client(args: argparse.Namespace) -> WebappSyncClient:
    return WebappSyncClient(url=args.webapp_url, token=args.token, timeout=args.timeout)


def export_snapshot(client: WebappSyncClient, *, sheet_names: list[str], limit_rows: int) -> dict[str, Any]:
    normalized_sheet_names = normalize_sheet_names(sheet_names)
    normalized_limit_rows = normalize_limit_rows(limit_rows)
    return client.export_sheet_snapshot(
        sheet_names=normalized_sheet_names,
        limit_rows=normalized_limit_rows,
    )


def sanitize_filename(value: str) -> str:
    return "".join(character if character.isalnum() or character in {"-", "_"} else "_" for character in value)


def write_json_file(file_path: Path, payload: dict[str, Any]) -> None:
    file_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def write_csv_file(file_path: Path, *, columns: list[str], rows: list[dict[str, Any]]) -> None:
    with file_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in columns})


def save_snapshot_artifacts(
    snapshot_payload: dict[str, Any],
    *,
    output_dir: Path,
    snapshot_label: str,
    export_format: str,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = output_dir / f"{sanitize_filename(snapshot_label)}-manifest.json"
    write_json_file(manifest_path, snapshot_payload)

    exported_files: dict[str, list[str]] = {"json": [str(manifest_path)], "csv": []}
    sheets_payload = snapshot_payload.get("sheets", {})
    for sheet_name, sheet_payload in sheets_payload.items():
        safe_sheet_name = sanitize_filename(sheet_name)
        base_path = output_dir / f"{sanitize_filename(snapshot_label)}-{safe_sheet_name}"
        if export_format in {"json", "both"}:
            json_path = base_path.with_suffix(".json")
            write_json_file(json_path, sheet_payload)
            exported_files["json"].append(str(json_path))
        if export_format in {"csv", "both"}:
            csv_path = base_path.with_suffix(".csv")
            write_csv_file(
                csv_path,
                columns=list(sheet_payload.get("columns", [])),
                rows=list(sheet_payload.get("rows", [])),
            )
            exported_files["csv"].append(str(csv_path))

    return {
        "output_dir": str(output_dir),
        "snapshot_label": snapshot_label,
        "files": exported_files,
    }


def build_snapshot_summary(snapshot_payload: dict[str, Any]) -> list[str]:
    summary_lines: list[str] = []
    for sheet_name, sheet_payload in snapshot_payload.get("sheets", {}).items():
        summary_lines.append(
            (
                f"- {sheet_name}: columnas={sheet_payload.get('column_count', 0)} "
                f"filas_exportadas={sheet_payload.get('returned_rows', 0)} "
                f"filas_totales={sheet_payload.get('total_rows', 0)} "
                f"truncado={sheet_payload.get('truncated', False)}"
            )
        )
    return summary_lines


def run_export(args: argparse.Namespace) -> dict[str, Any]:
    client = create_client(args)
    snapshot_payload = export_snapshot(
        client,
        sheet_names=args.sheets,
        limit_rows=args.limit_rows,
    )
    export_result = save_snapshot_artifacts(
        snapshot_payload,
        output_dir=args.output_dir,
        snapshot_label=args.snapshot_label,
        export_format=args.format,
    )
    LOGGER.info("Snapshot exportado en %s", export_result["output_dir"])
    for line in build_snapshot_summary(snapshot_payload):
        LOGGER.info(line)
    return {"snapshot": snapshot_payload, "artifacts": export_result}


def main() -> int:
    configure_logging()
    parser = build_parser()
    args = parser.parse_args()

    try:
        run_export(args)
    except Exception:
        LOGGER.exception("Falló la exportación de snapshot de hojas.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
