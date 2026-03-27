from __future__ import annotations

from services.modeling import DatasetCatalog, PredictionService, ModelRegistry


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
