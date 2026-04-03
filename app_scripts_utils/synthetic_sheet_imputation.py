#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests


ROOT_DIR = Path(__file__).resolve().parents[1]
APP_DIR = ROOT_DIR / "app"
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from config.settings import get_form_token, get_script_url
from services.modeling import DatasetCatalog, ModelRegistry, PredictionService
from services.synthetic_imputation import (
    DatasetCatalogFeatureResolver,
    SyntheticBatchBuilder,
    build_delete_batch_payload,
    build_projection_comments,
    export_projection_html,
    load_synthetic_scenarios,
)
from services.text_pipeline import CommentAnalyticsService


LOGGER = logging.getLogger(__name__)
DEFAULT_DATASET_PATH = ROOT_DIR / "app_scripts_utils" / "synthetic_sheet_imputation_dataset.json"


class WebappSyncClient:
    def __init__(self, *, url: str, token: str, timeout: int) -> None:
        self.url = url.strip()
        self.token = token.strip()
        self.timeout = timeout

    def post(self, action: str, payload: dict[str, Any]) -> dict[str, Any]:
        if not self.url:
            raise ValueError("Falta GOOGLE_SCRIPT_URL o --webapp-url.")
        if not self.token:
            raise ValueError("Falta GOOGLE_SCRIPT_TOKEN o --token.")

        response = requests.post(
            self.url,
            json={"token": self.token, "accion": action, **payload},
            timeout=self.timeout,
        )
        response.raise_for_status()
        data = response.json()
        if data.get("status") != "success":
            raise RuntimeError(f"El webapp devolvió error para {action}: {data.get('message', 'sin detalle')}")
        return data


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Flujo de prueba masiva para Google Sheet + Apps Script con datos sintéticos, "
            "vectorización MiniLM y render HTML 3D."
        )
    )
    parser.add_argument("--webapp-url", default=get_script_url(), help="URL del webapp desplegado de Apps Script.")
    parser.add_argument("--token", default=get_form_token(), help="Token compartido con Apps Script.")
    parser.add_argument("--timeout", type=int, default=30, help="Timeout HTTP en segundos.")
    parser.add_argument(
        "--dataset-file",
        type=Path,
        default=DEFAULT_DATASET_PATH,
        help="Archivo JSON versionable con escenarios sintéticos.",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    seed_parser = subparsers.add_parser("seed", help="Carga datos sintéticos al Google Sheet vía webapp.")
    seed_parser.add_argument("--test-batch-id", default=build_default_batch_id())

    render_parser = subparsers.add_parser(
        "render",
        help="Lee un lote sintético desde el webapp y exporta un HTML 3D.",
    )
    render_parser.add_argument("--test-batch-id", required=True)
    render_parser.add_argument("--exercise", required=True, choices=["default_risk", "credit_approval"])
    render_parser.add_argument(
        "--output-html",
        type=Path,
        default=None,
        help="Ruta del HTML 3D. Si se omite, se genera en data/processed/test_batches/.",
    )

    delete_parser = subparsers.add_parser(
        "delete",
        help="Prepara borrado por lote. Por defecto hace dry-run; usar --execute para borrar realmente.",
    )
    delete_parser.add_argument("--test-batch-id", required=True)
    delete_parser.add_argument("--execute", action="store_true", help="Ejecuta el borrado real del lote.")

    dry_run_parser = subparsers.add_parser(
        "delete-dry-run",
        help="Alias explícito para simular borrado en cascada de un lote sintético.",
    )
    dry_run_parser.add_argument("--test-batch-id", required=True)

    return parser


def build_default_batch_id() -> str:
    return datetime.now(timezone.utc).strftime("synthetic-batch-%Y%m%d-%H%M%S")


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s %(name)s - %(message)s",
    )


def create_client(args: argparse.Namespace) -> WebappSyncClient:
    return WebappSyncClient(url=args.webapp_url, token=args.token, timeout=args.timeout)


def run_seed(args: argparse.Namespace) -> None:
    scenarios = load_synthetic_scenarios(args.dataset_file)
    catalog = DatasetCatalog()
    predictor = PredictionService(ModelRegistry(catalog))
    builder = SyntheticBatchBuilder(
        feature_resolver=DatasetCatalogFeatureResolver(catalog),
        predictor=predictor,
    )
    batch = builder.build_batch(scenarios, test_batch_id=args.test_batch_id)
    client = create_client(args)

    for record in batch.records:
        client.post(
            "upsert_sesion",
            {
                "participant_id": record.participant_id,
                "public_alias": record.public_alias,
                "profile": record.profile,
                **record.traceability_payload,
            },
        )
        client.post(
            "upsert_respuesta",
            {
                "participant_id": record.participant_id,
                "exercise": record.exercise,
                "payload": record.progress_payload,
                **record.traceability_payload,
            },
        )
        client.post(
            "upsert_feedback",
            {
                "participant_id": record.participant_id,
                "exercise": record.exercise,
                "payload": record.feedback_payload,
                **record.traceability_payload,
            },
        )
        client.post(
            "marcar_completado",
            {
                "participant_id": record.participant_id,
                "exercise": record.exercise,
                **record.traceability_payload,
            },
        )

    LOGGER.info(
        "Seed completado.",
        extra={
            "test_batch_id": batch.test_batch_id,
            "records": batch.total_records,
            "exercises": batch.exercises,
        },
    )
    LOGGER.info("Lote sintético cargado: %s", batch.test_batch_id)
    LOGGER.info("Registros enviados: %s", batch.total_records)


def run_render(args: argparse.Namespace) -> None:
    client = create_client(args)
    batch_payload = client.post(
        "get_test_batch",
        {"test_batch_id": args.test_batch_id, "exercise": args.exercise},
    )
    comments = build_projection_comments(batch_payload, exercise=args.exercise)
    if not comments:
        raise RuntimeError(
            f"No se encontraron comentarios sintéticos para batch={args.test_batch_id} y exercise={args.exercise}."
        )

    projection = CommentAnalyticsService().build_projection(comments)
    output_path = args.output_html or (
        ROOT_DIR
        / "data"
        / "processed"
        / "test_batches"
        / f"{args.test_batch_id}-{args.exercise}-projection.html"
    )
    export_projection_html(
        projection,
        output_path=output_path,
        title=f"Proyección 3D sintética - {args.exercise}",
        test_batch_id=args.test_batch_id,
        exercise=args.exercise,
    )
    LOGGER.info("HTML 3D exportado en: %s", output_path)


def run_delete(args: argparse.Namespace, *, dry_run_override: bool | None = None) -> None:
    dry_run = (not getattr(args, "execute", False)) if dry_run_override is None else dry_run_override
    client = create_client(args)
    response = client.post(
        "delete_test_batch",
        build_delete_batch_payload(args.test_batch_id, dry_run=dry_run),
    )
    LOGGER.info(
        "Resultado delete_test_batch: %s",
        json.dumps(response, ensure_ascii=False, indent=2),
    )


def main() -> int:
    configure_logging()
    parser = build_parser()
    args = parser.parse_args()

    try:
        if args.command == "seed":
            run_seed(args)
        elif args.command == "render":
            run_render(args)
        elif args.command == "delete":
            run_delete(args)
        elif args.command == "delete-dry-run":
            run_delete(args, dry_run_override=True)
        else:
            parser.error(f"Comando no soportado: {args.command}")
    except Exception:
        LOGGER.exception("Falló la ejecución del flujo sintético.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
