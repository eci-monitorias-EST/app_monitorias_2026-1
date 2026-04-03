from __future__ import annotations

from pathlib import Path
from typing import Any

from domain.models import PredictionResult
from services.synthetic_imputation import (
    SyntheticBatchBuilder,
    SyntheticFeedbackSpec,
    SyntheticScenarioSpec,
    build_delete_batch_payload,
    build_projection_comments,
    load_synthetic_scenarios,
)


class _ResolverStub:
    def resolve_features(self, exercise: str, dataset_row_index: int) -> dict[str, Any]:
        return {
            "exercise": exercise,
            "dataset_row_index": dataset_row_index,
            "score": 7,
        }


class _PredictorStub:
    def predict(self, exercise: str, features: dict[str, Any]) -> PredictionResult:
        return PredictionResult(
            exercise=exercise,
            probability=0.73,
            label="Sintético",
            features=features,
            provider="stub",
            local_explanations={"lime": {"items": []}, "shap_local": {"items": []}},
            global_explanations={"shap_global": {"items": []}},
            pedagogical_summary="Resumen sintético",
        )


def test_load_synthetic_scenarios_reads_versioned_fixture() -> None:
    fixture_path = Path(__file__).resolve().parents[1] / "app_scripts_utils" / "synthetic_sheet_imputation_dataset.json"

    scenarios = load_synthetic_scenarios(fixture_path)

    assert len(scenarios) == 8
    assert {scenario.exercise for scenario in scenarios} == {"credit_approval", "default_risk"}


def test_batch_builder_marks_records_with_traceability() -> None:
    builder = SyntheticBatchBuilder(
        feature_resolver=_ResolverStub(),
        predictor=_PredictorStub(),
    )
    scenarios = [
        SyntheticScenarioSpec(
            scenario_id="scenario-001",
            exercise="default_risk",
            dataset_row_index=4,
            profile={"nombre": "Ada", "colegio": "Colegio Demo", "edad": 16},
            dataset_comment="Comentario sobre dataset",
            analytics_comment="Comentario analítico",
            prediction_reflection="Comentario de reflexión",
            feedback=SyntheticFeedbackSpec(
                rating=5,
                summary="Buen ejercicio",
                missing_topics="Más ejemplos",
                improvement_ideas="Agregar comparaciones",
            ),
        )
    ]

    batch = builder.build_batch(scenarios, test_batch_id="batch-123")

    assert batch.total_records == 1
    record = batch.records[0]
    assert record.participant_id == "synthetic-batch-123-001"
    assert record.public_alias == "TEST-001"
    assert record.traceability_payload == {
        "is_test_data": True,
        "test_batch_id": "batch-123",
        "data_origin": "synthetic_mass_imputation",
    }
    assert record.profile["nombre"].startswith("SINTÉTICO")
    assert "sintético" in record.profile["colegio"].lower()
    assert record.progress_payload["dataset_comment"].startswith("[DATOS_SINTETICOS|batch=batch-123]")
    assert record.feedback_payload["summary"].startswith("[DATOS_SINTETICOS|batch=batch-123]")
    assert record.progress_payload["prediction_output"]["provider"] == "stub"


def test_build_projection_comments_joins_session_alias_and_filters_exercise() -> None:
    batch_payload = {
        "sesiones": [{"participant_id": "p-1", "public_alias": "TEST-001"}],
        "respuestas": [
            {
                "participant_id": "p-1",
                "exercise": "default_risk",
                "dataset_comment": "uno",
                "analytics_comment": "dos",
                "prediction_reflection": "tres",
            },
            {
                "participant_id": "p-2",
                "exercise": "credit_approval",
                "dataset_comment": "no",
                "analytics_comment": "entra",
                "prediction_reflection": "acá",
            },
        ],
    }

    comments = build_projection_comments(batch_payload, exercise="default_risk")

    assert len(comments) == 1
    assert comments[0].public_alias == "TEST-001"
    assert comments[0].combined_comment == "uno dos tres"


def test_build_delete_batch_payload_requires_confirmation_only_for_real_delete() -> None:
    dry_run_payload = build_delete_batch_payload("batch-123", dry_run=True)
    execute_payload = build_delete_batch_payload("batch-123", dry_run=False)

    assert dry_run_payload == {"test_batch_id": "batch-123", "dry_run": True}
    assert execute_payload == {
        "test_batch_id": "batch-123",
        "dry_run": False,
        "confirm_phrase": "DELETE_TEST_BATCH",
    }
