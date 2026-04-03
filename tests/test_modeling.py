from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd

from domain.models import ExerciseOption
from services.modeling import DatasetCatalog, PredictionService, ModelRegistry


@dataclass
class _FakeBundle:
    exercise: str
    label: str


class _FakeClassifier:
    def __init__(self, classes_: list[int]) -> None:
        self.classes_ = classes_


class _FakePipeline:
    def __init__(self) -> None:
        self.named_steps = {"classifier": _FakeClassifier([0, 1])}

    def predict_proba(self, _: pd.DataFrame) -> list[list[float]]:
        return [[0.9, 0.1]]


class _FakeExplainer:
    def build_linear_explanations(
        self, pipeline: _FakePipeline, inputs: dict[str, Any]
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        del pipeline, inputs
        return (
            {"items": [{"feature": "f1", "impact": 0.2}]},
            {"items": [{"feature": "f1", "importance": 0.2}]},
        )


class _FakeAgent:
    def explain(
        self,
        exercise_label: str,
        prediction_label: str,
        probability: float,
        local_items: list[dict[str, Any]],
    ) -> str:
        del local_items
        return f"{exercise_label}: {prediction_label} ({probability:.1%})"


class _FakeRegistry:
    def get_model(self, exercise: str) -> tuple[_FakePipeline, _FakeBundle]:
        return _FakePipeline(), _FakeBundle(exercise=exercise, label="Aprobación de crédito")


def test_catalog_loads_official_german_dataset() -> None:
    catalog = DatasetCatalog()
    bundle = catalog.load_credit_approval()

    assert bundle.df.shape[0] > 0
    assert "credit_outcome" in bundle.df.columns
    assert bundle.demo_mode is False


def test_prediction_returns_explanations() -> None:
    catalog = DatasetCatalog()
    registry = ModelRegistry(catalog)
    service = PredictionService(registry)
    bundle = catalog.load_default_risk()
    sample = bundle.df[bundle.features].iloc[0].to_dict()

    result = service.predict("default_risk", sample)

    assert 0.0 <= result.probability <= 1.0
    assert result.local_explanations["lime"]["items"]
    assert result.global_explanations["shap_global"]["items"]


def test_credit_approval_uses_explicit_positive_class_probability() -> None:
    service = PredictionService(_FakeRegistry())
    service.explainer = _FakeExplainer()
    service.agent = _FakeAgent()

    result = service.predict(ExerciseOption.CREDIT_APPROVAL, {"f1": 1})

    assert result.probability == 0.1
    assert result.label == "Requiere revisión"
