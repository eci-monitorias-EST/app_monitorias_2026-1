from __future__ import annotations

import importlib.util
from argparse import Namespace
from pathlib import Path
from typing import Any

import requests

from domain.models import PredictionResult
from services.synthetic_imputation import (
    SyntheticBatchBuilder,
    SyntheticBatch,
    SyntheticFeedbackSpec,
    SyntheticScenarioSpec,
    build_delete_batch_payload,
    build_seed_batch_payload,
    build_projection_comments,
    chunk_synthetic_batch,
    expand_scenarios_to_minimum,
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


def _load_synthetic_script_module() -> Any:
    script_path = Path(__file__).resolve().parents[1] / "app_scripts_utils" / "synthetic_sheet_imputation.py"
    spec = importlib.util.spec_from_file_location("synthetic_sheet_imputation_script", script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("No se pudo cargar synthetic_sheet_imputation.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_load_synthetic_scenarios_reads_versioned_fixture() -> None:
    fixture_path = Path(__file__).resolve().parents[1] / "app_scripts_utils" / "synthetic_sheet_imputation_dataset.json"

    scenarios = load_synthetic_scenarios(fixture_path)

    assert len(scenarios) == 100
    assert {scenario.exercise for scenario in scenarios} == {"credit_approval", "default_risk"}


def test_expand_scenarios_to_minimum_replicates_base_templates_until_target() -> None:
    base_scenarios = [
        SyntheticScenarioSpec(
            scenario_id="scenario-001",
            exercise="default_risk",
            dataset_row_index=0,
            profile={"nombre": "Ada", "colegio": "Colegio Demo"},
            dataset_comment="Comentario base",
            analytics_comment="Analítica base",
            prediction_reflection="Reflexión base",
            feedback=SyntheticFeedbackSpec(
                rating=5,
                summary="Resumen base",
                missing_topics="Temas base",
                improvement_ideas="Ideas base",
            ),
        ),
        SyntheticScenarioSpec(
            scenario_id="scenario-002",
            exercise="credit_approval",
            dataset_row_index=1,
            profile={"nombre": "Bruno", "colegio": "Colegio Demo"},
            dataset_comment="Comentario dos",
            analytics_comment="Analítica dos",
            prediction_reflection="Reflexión dos",
            feedback=SyntheticFeedbackSpec(
                rating=4,
                summary="Resumen dos",
                missing_topics="Temas dos",
                improvement_ideas="Ideas dos",
            ),
        ),
    ]

    expanded = expand_scenarios_to_minimum(base_scenarios, minimum_records=5)

    assert len(expanded) == 5
    assert expanded[0].scenario_id.endswith("v01-b01")
    assert expanded[1].scenario_id.endswith("v01-b02")
    assert expanded[2].scenario_id.endswith("v02-b01")
    assert "Variante v01-b01." in expanded[0].dataset_comment
    assert expanded[0].profile["nombre"].endswith("v01-b01")


def test_expand_scenarios_to_minimum_balances_exercises_when_both_are_present() -> None:
    base_scenarios = [
        SyntheticScenarioSpec(
            scenario_id="scenario-001",
            exercise="default_risk",
            dataset_row_index=0,
            profile={"nombre": "Ada", "colegio": "Colegio Demo"},
            dataset_comment="Comentario 1",
            analytics_comment="Analítica 1",
            prediction_reflection="Reflexión 1",
            feedback=SyntheticFeedbackSpec(
                rating=5,
                summary="Resumen 1",
                missing_topics="Temas 1",
                improvement_ideas="Ideas 1",
            ),
        ),
        SyntheticScenarioSpec(
            scenario_id="scenario-002",
            exercise="default_risk",
            dataset_row_index=1,
            profile={"nombre": "Bruno", "colegio": "Colegio Demo"},
            dataset_comment="Comentario 2",
            analytics_comment="Analítica 2",
            prediction_reflection="Reflexión 2",
            feedback=SyntheticFeedbackSpec(
                rating=4,
                summary="Resumen 2",
                missing_topics="Temas 2",
                improvement_ideas="Ideas 2",
            ),
        ),
        SyntheticScenarioSpec(
            scenario_id="scenario-003",
            exercise="default_risk",
            dataset_row_index=2,
            profile={"nombre": "Carla", "colegio": "Colegio Demo"},
            dataset_comment="Comentario 3",
            analytics_comment="Analítica 3",
            prediction_reflection="Reflexión 3",
            feedback=SyntheticFeedbackSpec(
                rating=5,
                summary="Resumen 3",
                missing_topics="Temas 3",
                improvement_ideas="Ideas 3",
            ),
        ),
        SyntheticScenarioSpec(
            scenario_id="scenario-004",
            exercise="credit_approval",
            dataset_row_index=3,
            profile={"nombre": "Delfina", "colegio": "Colegio Demo"},
            dataset_comment="Comentario 4",
            analytics_comment="Analítica 4",
            prediction_reflection="Reflexión 4",
            feedback=SyntheticFeedbackSpec(
                rating=3,
                summary="Resumen 4",
                missing_topics="Temas 4",
                improvement_ideas="Ideas 4",
            ),
        ),
    ]

    expanded = expand_scenarios_to_minimum(base_scenarios, minimum_records=8)

    exercises = [scenario.exercise for scenario in expanded]

    assert len(expanded) == 8
    assert exercises.count("default_risk") == 4
    assert exercises.count("credit_approval") == 4
    assert exercises[:4] == ["default_risk", "credit_approval", "default_risk", "credit_approval"]


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
    assert record.profile["sexo"] == "Femenino"
    assert 14 <= record.profile["edad"] <= 25
    assert record.profile["grado"] in {"10", "11"}


def test_batch_builder_normalizes_gender_age_and_grade_ranges() -> None:
    builder = SyntheticBatchBuilder(
        feature_resolver=_ResolverStub(),
        predictor=_PredictorStub(),
    )
    scenarios = [
        SyntheticScenarioSpec(
            scenario_id="scenario-001",
            exercise="default_risk",
            dataset_row_index=4,
            profile={
                "nombre": "Alex",
                "colegio": "Colegio Demo",
                "edad": 30,
                "grado": "noveno",
                "sexo": "M",
            },
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

    batch = builder.build_batch(scenarios, test_batch_id="batch-normalize")
    profile = batch.records[0].profile

    assert profile["sexo"] == "Masculino"
    assert profile["edad"] == 25
    assert profile["grado"] == "10"


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


def test_chunk_synthetic_batch_and_build_seed_batch_payload_keep_traceability() -> None:
    builder = SyntheticBatchBuilder(
        feature_resolver=_ResolverStub(),
        predictor=_PredictorStub(),
    )
    scenarios = [
        SyntheticScenarioSpec(
            scenario_id=f"scenario-{index:03d}",
            exercise="default_risk",
            dataset_row_index=index,
            profile={"nombre": f"Ada {index}", "colegio": "Colegio Demo", "edad": 16},
            dataset_comment=f"Comentario {index}",
            analytics_comment=f"Analítica {index}",
            prediction_reflection=f"Reflexión {index}",
            feedback=SyntheticFeedbackSpec(
                rating=5,
                summary=f"Resumen {index}",
                missing_topics=f"Temas {index}",
                improvement_ideas=f"Ideas {index}",
            ),
        )
        for index in range(3)
    ]

    batch = builder.build_batch(scenarios, test_batch_id="batch-456")

    chunks = chunk_synthetic_batch(batch, chunk_size=2)

    assert [chunk.records_count for chunk in chunks] == [2, 1]
    assert [(chunk.chunk_index, chunk.total_chunks) for chunk in chunks] == [(1, 2), (2, 2)]

    payload = build_seed_batch_payload(chunks[0], test_batch_id=batch.test_batch_id)

    assert payload["test_batch_id"] == "batch-456"
    assert payload["chunk_index"] == 1
    assert payload["total_chunks"] == 2
    assert payload["records_count"] == 2
    assert payload["records"][0]["traceability_payload"] == {
        "is_test_data": True,
        "test_batch_id": "batch-456",
        "data_origin": "synthetic_mass_imputation",
    }
    assert payload["records"][0]["progress_payload"]["dataset_comment"].startswith(
        "[DATOS_SINTETICOS|batch=batch-456]"
    )


def test_chunk_synthetic_batch_rejects_non_positive_chunk_size() -> None:
    batch = SyntheticBatch(test_batch_id="batch-789", records=[])

    try:
        chunk_synthetic_batch(batch, chunk_size=0)
    except ValueError as error:
        assert "chunk_size" in str(error)
    else:
        raise AssertionError("Se esperaba ValueError para chunk_size inválido")


def test_webapp_sync_client_posts_expected_payload(monkeypatch: Any) -> None:
    module = _load_synthetic_script_module()
    captured: dict[str, Any] = {}

    class _ResponseStub:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, Any]:
            return {"status": "success", "processed_records": 2}

    def _fake_post(url: str, *, json: dict[str, Any], timeout: int) -> _ResponseStub:
        captured["url"] = url
        captured["json"] = json
        captured["timeout"] = timeout
        return _ResponseStub()

    monkeypatch.setattr(requests, "post", _fake_post)

    client = module.WebappSyncClient(url="https://example.test/webapp", token="token-123", timeout=45)
    response = client.post("seed_test_batch", {"records_count": 2})

    assert response == {"status": "success", "processed_records": 2}
    assert captured == {
        "url": "https://example.test/webapp",
        "json": {"token": "token-123", "accion": "seed_test_batch", "records_count": 2},
        "timeout": 45,
    }


def test_run_seed_uses_batch_endpoint_with_configurable_chunks(monkeypatch: Any) -> None:
    module = _load_synthetic_script_module()

    scenarios = [
        SyntheticScenarioSpec(
            scenario_id=f"scenario-{index:03d}",
            exercise="credit_approval",
            dataset_row_index=index,
            profile={"nombre": f"Bruno {index}", "colegio": "Colegio Demo", "edad": 17},
            dataset_comment=f"Comentario {index}",
            analytics_comment=f"Analítica {index}",
            prediction_reflection=f"Reflexión {index}",
            feedback=SyntheticFeedbackSpec(
                rating=4,
                summary=f"Resumen {index}",
                missing_topics=f"Temas {index}",
                improvement_ideas=f"Ideas {index}",
            ),
        )
        for index in range(5)
    ]
    builder = SyntheticBatchBuilder(feature_resolver=_ResolverStub(), predictor=_PredictorStub())
    batch = builder.build_batch(scenarios, test_batch_id="batch-seed")
    requests_sent: list[tuple[str, dict[str, Any]]] = []

    class _ClientStub:
        def post(self, action: str, payload: dict[str, Any]) -> dict[str, Any]:
            requests_sent.append((action, payload))
            if action == "seed_test_batch":
                return {"status": "success"}
            if action == "get_test_batch":
                return {
                    "status": "success",
                    "sesiones": [{} for _ in range(batch.total_records)],
                    "respuestas": [{} for _ in range(batch.total_records)],
                }
            raise AssertionError(f"Acción inesperada: {action}")

    class _BatchBuilderStub:
        def __init__(self, **_: Any) -> None:
            return None

        def build_batch(self, _: list[SyntheticScenarioSpec], *, test_batch_id: str) -> SyntheticBatch:
            assert test_batch_id == "batch-seed"
            return batch

    monkeypatch.setattr(module, "load_synthetic_scenarios", lambda *args, **kwargs: scenarios)
    monkeypatch.setattr(module, "DatasetCatalog", lambda: object())
    monkeypatch.setattr(module, "ModelRegistry", lambda catalog: object())
    monkeypatch.setattr(module, "PredictionService", lambda registry: object())
    monkeypatch.setattr(module, "SyntheticBatchBuilder", _BatchBuilderStub)
    monkeypatch.setattr(module, "create_client", lambda args: _ClientStub())

    args = Namespace(
        dataset_file=Path("irrelevant.json"),
        minimum_records=5,
        test_batch_id="batch-seed",
        chunk_size=2,
        webapp_url="https://example.test/webapp",
        token="token-123",
        timeout=30,
    )

    module.run_seed(args)

    assert len(requests_sent) == 4
    assert [action for action, _ in requests_sent] == [
        "seed_test_batch",
        "seed_test_batch",
        "seed_test_batch",
        "get_test_batch",
    ]
    assert [payload["records_count"] for _, payload in requests_sent[:3]] == [2, 2, 1]
    assert [payload["chunk_index"] for _, payload in requests_sent[:3]] == [1, 2, 3]
    assert all(payload["total_chunks"] == 3 for _, payload in requests_sent[:3])
    assert requests_sent[3][1] == {"test_batch_id": "batch-seed", "exercise": "credit_approval"}


def test_verify_seed_batch_visibility_retries_with_short_backoff(monkeypatch: Any) -> None:
    module = _load_synthetic_script_module()
    builder = SyntheticBatchBuilder(feature_resolver=_ResolverStub(), predictor=_PredictorStub())
    batch = builder.build_batch(
        [
            SyntheticScenarioSpec(
                scenario_id="scenario-001",
                exercise="default_risk",
                dataset_row_index=0,
                profile={"nombre": "Ada", "colegio": "Colegio Demo", "edad": 16},
                dataset_comment="Comentario 1",
                analytics_comment="Analítica 1",
                prediction_reflection="Reflexión 1",
                feedback=SyntheticFeedbackSpec(
                    rating=5,
                    summary="Resumen 1",
                    missing_topics="Temas 1",
                    improvement_ideas="Ideas 1",
                ),
            ),
            SyntheticScenarioSpec(
                scenario_id="scenario-002",
                exercise="credit_approval",
                dataset_row_index=1,
                profile={"nombre": "Bruno", "colegio": "Colegio Demo", "edad": 17},
                dataset_comment="Comentario 2",
                analytics_comment="Analítica 2",
                prediction_reflection="Reflexión 2",
                feedback=SyntheticFeedbackSpec(
                    rating=4,
                    summary="Resumen 2",
                    missing_topics="Temas 2",
                    improvement_ideas="Ideas 2",
                ),
            ),
        ],
        test_batch_id="batch-verify",
    )

    sleep_calls: list[float] = []
    verification_attempts = {"count": 0}
    requests_sent: list[tuple[str, dict[str, Any]]] = []

    class _ClientStub:
        def post(self, action: str, payload: dict[str, Any]) -> dict[str, Any]:
            requests_sent.append((action, payload))
            assert action == "get_test_batch"
            verification_attempts["count"] += 1
            if verification_attempts["count"] <= 2:
                return {"status": "success", "sesiones": [], "respuestas": []}
            return {
                "status": "success",
                "sesiones": [{} for _ in range(batch.total_records)],
                "respuestas": [{}],
            }

    monkeypatch.setattr(module.time, "sleep", lambda seconds: sleep_calls.append(seconds))

    module.verify_seed_batch_visibility(
        _ClientStub(),
        batch,
        max_attempts=3,
        initial_backoff_seconds=0.25,
    )

    assert sleep_calls == [0.25]
    assert verification_attempts["count"] == 4
    assert requests_sent == [
        ("get_test_batch", {"test_batch_id": "batch-verify", "exercise": "credit_approval"}),
        ("get_test_batch", {"test_batch_id": "batch-verify", "exercise": "default_risk"}),
        ("get_test_batch", {"test_batch_id": "batch-verify", "exercise": "credit_approval"}),
        ("get_test_batch", {"test_batch_id": "batch-verify", "exercise": "default_risk"}),
    ]


def test_verify_delete_batch_visibility_retries_until_all_sheets_are_empty(monkeypatch: Any) -> None:
    module = _load_synthetic_script_module()
    sleep_calls: list[float] = []
    requests_sent: list[tuple[str, dict[str, Any]]] = []
    remaining_payloads = [
        {
            "status": "success",
            "sesiones": [{}],
            "respuestas": [],
            "historial_comentarios": [],
            "feedback": [],
            "control": [{}],
        },
        {
            "status": "success",
            "sesiones": [],
            "respuestas": [],
            "historial_comentarios": [],
            "feedback": [],
            "control": [],
        },
    ]

    class _ClientStub:
        def post(self, action: str, payload: dict[str, Any]) -> dict[str, Any]:
            requests_sent.append((action, payload))
            assert action == "get_test_batch"
            return remaining_payloads.pop(0)

    monkeypatch.setattr(module.time, "sleep", lambda seconds: sleep_calls.append(seconds))

    module.verify_delete_batch_visibility(
        _ClientStub(),
        "batch-delete",
        max_attempts=3,
        initial_backoff_seconds=0.5,
    )

    assert sleep_calls == [0.5]
    assert requests_sent == [
        ("get_test_batch", {"test_batch_id": "batch-delete", "exercise": ""}),
        ("get_test_batch", {"test_batch_id": "batch-delete", "exercise": ""}),
    ]


def test_run_delete_executes_post_delete_verification_only_for_real_delete(monkeypatch: Any) -> None:
    module = _load_synthetic_script_module()
    requests_sent: list[tuple[str, dict[str, Any]]] = []
    verify_calls: list[tuple[str, int, float]] = []

    class _ClientStub:
        def post(self, action: str, payload: dict[str, Any]) -> dict[str, Any]:
            requests_sent.append((action, payload))
            return {"status": "success", "action": action}

    monkeypatch.setattr(module, "create_client", lambda args: _ClientStub())
    monkeypatch.setattr(
        module,
        "verify_delete_batch_visibility",
        lambda client, test_batch_id, *, max_attempts, initial_backoff_seconds: verify_calls.append(
            (test_batch_id, max_attempts, initial_backoff_seconds)
        ),
    )

    dry_run_args = Namespace(
        test_batch_id="batch-delete",
        execute=False,
        verify_attempts=7,
        verify_backoff_seconds=1.25,
    )
    execute_args = Namespace(
        test_batch_id="batch-delete",
        execute=True,
        verify_attempts=5,
        verify_backoff_seconds=2.5,
    )

    module.run_delete(dry_run_args)
    module.run_delete(execute_args)

    assert requests_sent == [
        ("delete_test_batch", {"test_batch_id": "batch-delete", "dry_run": True}),
        (
            "delete_test_batch",
            {
                "test_batch_id": "batch-delete",
                "dry_run": False,
                "confirm_phrase": "DELETE_TEST_BATCH",
            },
        ),
    ]
    assert verify_calls == [("batch-delete", 5, 2.5)]
