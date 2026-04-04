#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import logging
import sys
import time
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
from services.modeling import DatasetCatalog, ModelRegistry, PredictionService
from services.synthetic_imputation import (
    DatasetCatalogFeatureResolver,
    SyntheticBatchBuilder,
    build_delete_batch_payload,
    build_seed_batch_payload,
    build_projection_comments,
    chunk_synthetic_batch,
    export_projection_html,
    load_synthetic_scenarios,
)
from services.text_pipeline import CommentAnalyticsService


LOGGER = logging.getLogger(__name__)
DEFAULT_DATASET_PATH = ROOT_DIR / "app_scripts_utils" / "synthetic_sheet_imputation_dataset.json"
SEED_VERIFY_MAX_ATTEMPTS = 3
SEED_VERIFY_INITIAL_BACKOFF_SECONDS = 0.5
DELETE_VERIFY_MAX_ATTEMPTS = 4
DELETE_VERIFY_INITIAL_BACKOFF_SECONDS = 1.0


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
    parser.add_argument(
        "--minimum-records",
        type=int,
        default=100,
        help="Cantidad mínima de registros sintéticos a generar a partir de los escenarios base.",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    seed_parser = subparsers.add_parser("seed", help="Carga datos sintéticos al Google Sheet vía webapp.")
    seed_parser.add_argument("--test-batch-id", default=build_default_batch_id())
    seed_parser.add_argument(
        "--chunk-size",
        type=int,
        default=25,
        help="Cantidad de registros por request batch hacia Apps Script.",
    )

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
    delete_parser.add_argument(
        "--verify-attempts",
        type=int,
        default=DELETE_VERIFY_MAX_ATTEMPTS,
        help="Cantidad de chequeos post-delete cuando se usa --execute.",
    )
    delete_parser.add_argument(
        "--verify-backoff-seconds",
        type=float,
        default=DELETE_VERIFY_INITIAL_BACKOFF_SECONDS,
        help="Backoff inicial entre chequeos post-delete.",
    )

    dry_run_parser = subparsers.add_parser(
        "delete-dry-run",
        help="Alias explícito para simular borrado en cascada de un lote sintético.",
    )
    dry_run_parser.add_argument("--test-batch-id", required=True)
    dry_run_parser.add_argument(
        "--verify-attempts",
        type=int,
        default=DELETE_VERIFY_MAX_ATTEMPTS,
        help="Se ignora en dry-run; se conserva para compatibilidad de CLI.",
    )
    dry_run_parser.add_argument(
        "--verify-backoff-seconds",
        type=float,
        default=DELETE_VERIFY_INITIAL_BACKOFF_SECONDS,
        help="Se ignora en dry-run; se conserva para compatibilidad de CLI.",
    )

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
    scenarios = load_synthetic_scenarios(args.dataset_file, minimum_records=args.minimum_records)
    catalog = DatasetCatalog()
    predictor = PredictionService(ModelRegistry(catalog))
    builder = SyntheticBatchBuilder(
        feature_resolver=DatasetCatalogFeatureResolver(catalog),
        predictor=predictor,
    )
    batch = builder.build_batch(scenarios, test_batch_id=args.test_batch_id)
    client = create_client(args)
    chunks = chunk_synthetic_batch(batch, chunk_size=args.chunk_size)

    for chunk in chunks:
        payload = build_seed_batch_payload(chunk, test_batch_id=batch.test_batch_id)
        client.post("seed_test_batch", payload)
        LOGGER.info(
            "Chunk batch enviado al webapp.",
            extra={
                "test_batch_id": batch.test_batch_id,
                "chunk_index": chunk.chunk_index,
                "total_chunks": chunk.total_chunks,
                "records_count": chunk.records_count,
            },
        )

    verify_seed_batch_visibility(client, batch)

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
    LOGGER.info("Chunks enviados: %s", len(chunks))


def verify_seed_batch_visibility(
    client: WebappSyncClient,
    batch: Any,
    *,
    max_attempts: int = SEED_VERIFY_MAX_ATTEMPTS,
    initial_backoff_seconds: float = SEED_VERIFY_INITIAL_BACKOFF_SECONDS,
) -> None:
    if max_attempts <= 0:
        raise ValueError("max_attempts debe ser mayor que cero.")
    if initial_backoff_seconds <= 0:
        raise ValueError("initial_backoff_seconds debe ser mayor que cero.")

    expected_by_exercise = _count_records_by_exercise(batch.records)
    last_observed_state = "sin observaciones"

    for attempt in range(1, max_attempts + 1):
        verification_errors: list[str] = []
        for exercise, expected_records in sorted(expected_by_exercise.items()):
            payload = client.post(
                "get_test_batch",
                {"test_batch_id": batch.test_batch_id, "exercise": exercise},
            )
            observed_sessions = len(payload.get("sesiones", []))
            observed_responses = len(payload.get("respuestas", []))
            last_observed_state = (
                f"exercise={exercise} sesiones={observed_sessions}/{batch.total_records} "
                f"respuestas={observed_responses}/{expected_records}"
            )
            if observed_sessions < batch.total_records or observed_responses < expected_records:
                verification_errors.append(last_observed_state)

        if not verification_errors:
            LOGGER.info(
                "Verificación post-seed confirmada.",
                extra={
                    "test_batch_id": batch.test_batch_id,
                    "attempt": attempt,
                    "exercises": tuple(sorted(expected_by_exercise)),
                },
            )
            return

        if attempt == max_attempts:
            break

        backoff_seconds = initial_backoff_seconds * (2 ** (attempt - 1))
        LOGGER.warning(
            "Lote aún no visible tras seed; reintentando verificación.",
            extra={
                "test_batch_id": batch.test_batch_id,
                "attempt": attempt,
                "max_attempts": max_attempts,
                "backoff_seconds": backoff_seconds,
                "details": verification_errors,
            },
        )
        time.sleep(backoff_seconds)

    raise RuntimeError(
        "El lote sintético no quedó visible tras el seed. "
        f"batch={batch.test_batch_id} último_estado={last_observed_state}"
    )


def _count_records_by_exercise(records: list[Any]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for record in records:
        counts[record.exercise] = counts.get(record.exercise, 0) + 1
    return counts


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
    if not dry_run:
        verify_delete_batch_visibility(
            client,
            args.test_batch_id,
            max_attempts=getattr(args, "verify_attempts", DELETE_VERIFY_MAX_ATTEMPTS),
            initial_backoff_seconds=getattr(
                args,
                "verify_backoff_seconds",
                DELETE_VERIFY_INITIAL_BACKOFF_SECONDS,
            ),
        )


def verify_delete_batch_visibility(
    client: WebappSyncClient,
    test_batch_id: str,
    *,
    max_attempts: int = DELETE_VERIFY_MAX_ATTEMPTS,
    initial_backoff_seconds: float = DELETE_VERIFY_INITIAL_BACKOFF_SECONDS,
) -> None:
    if max_attempts <= 0:
        raise ValueError("max_attempts debe ser mayor que cero.")
    if initial_backoff_seconds <= 0:
        raise ValueError("initial_backoff_seconds debe ser mayor que cero.")

    last_observed_state = "sin observaciones"
    for attempt in range(1, max_attempts + 1):
        payload = client.post("get_test_batch", {"test_batch_id": test_batch_id, "exercise": ""})
        remaining_by_sheet = {
            "sesiones": len(payload.get("sesiones", [])),
            "respuestas": len(payload.get("respuestas", [])),
            "historial_comentarios": len(payload.get("historial_comentarios", [])),
            "feedback": len(payload.get("feedback", [])),
            "control": len(payload.get("control", [])),
        }
        remaining_total = sum(remaining_by_sheet.values())
        last_observed_state = json.dumps(remaining_by_sheet, ensure_ascii=False, sort_keys=True)

        if remaining_total == 0:
            LOGGER.info(
                "Verificación post-delete confirmada.",
                extra={
                    "test_batch_id": test_batch_id,
                    "attempt": attempt,
                },
            )
            return

        if attempt == max_attempts:
            break

        backoff_seconds = initial_backoff_seconds * (2 ** (attempt - 1))
        LOGGER.warning(
            "Persisten filas sintéticas tras delete; reintentando verificación.",
            extra={
                "test_batch_id": test_batch_id,
                "attempt": attempt,
                "max_attempts": max_attempts,
                "backoff_seconds": backoff_seconds,
                "remaining_by_sheet": remaining_by_sheet,
            },
        )
        time.sleep(backoff_seconds)

    raise RuntimeError(
        "El lote sintético sigue visible tras delete_test_batch. "
        f"batch={test_batch_id} último_estado={last_observed_state}"
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
