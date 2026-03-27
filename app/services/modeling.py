from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from domain.models import ExerciseOption, PredictionResult, VariableDescriptor


ROOT_DIR = Path(__file__).resolve().parents[2]


GERMAN_VARIABLES = [
    VariableDescriptor("status_checking_account", "Cuenta corriente", "Estado de la cuenta corriente del solicitante.", "categorical", "UCI Statlog German Credit Data", "Status of existing checking account"),
    VariableDescriptor("duration_month", "Duración del crédito", "Duración del crédito en meses.", "numeric", "UCI Statlog German Credit Data", "Duration in month"),
    VariableDescriptor("credit_history", "Historial crediticio", "Comportamiento crediticio previo del solicitante.", "categorical", "UCI Statlog German Credit Data", "Credit history"),
    VariableDescriptor("purpose", "Propósito del crédito", "Uso principal del crédito solicitado.", "categorical", "UCI Statlog German Credit Data", "Purpose"),
    VariableDescriptor("credit_amount", "Monto del crédito", "Monto solicitado por el cliente.", "numeric", "UCI Statlog German Credit Data", "Credit amount"),
    VariableDescriptor("savings_account", "Ahorros / bonos", "Nivel de ahorro o bonos declarados.", "categorical", "UCI Statlog German Credit Data", "Savings account/bonds"),
    VariableDescriptor("employment_since", "Antigüedad laboral", "Tiempo de empleo en la posición actual.", "categorical", "UCI Statlog German Credit Data", "Present employment since"),
    VariableDescriptor("installment_rate", "Tasa de cuota", "Cuota como porcentaje del ingreso disponible.", "numeric", "UCI Statlog German Credit Data", "Installment rate in percentage of disposable income"),
    VariableDescriptor("personal_status_sex", "Estado personal y sexo", "Perfil personal codificado en el dataset.", "categorical", "UCI Statlog German Credit Data", "Personal status and sex"),
    VariableDescriptor("other_debtors", "Otros deudores", "Existencia de codeudores o garantes.", "categorical", "UCI Statlog German Credit Data", "Other debtors / guarantors"),
    VariableDescriptor("present_residence_since", "Antigüedad residencia", "Tiempo en la residencia actual.", "numeric", "UCI Statlog German Credit Data", "Present residence since"),
    VariableDescriptor("property", "Tipo de propiedad", "Tipo de activo o propiedad declarada.", "categorical", "UCI Statlog German Credit Data", "Property"),
    VariableDescriptor("age_years", "Edad", "Edad del solicitante en años.", "numeric", "UCI Statlog German Credit Data", "Age in years"),
    VariableDescriptor("other_installment_plans", "Otros planes de pago", "Existencia de otros planes de pago.", "categorical", "UCI Statlog German Credit Data", "Other installment plans"),
    VariableDescriptor("housing", "Vivienda", "Situación de vivienda del solicitante.", "categorical", "UCI Statlog German Credit Data", "Housing"),
    VariableDescriptor("existing_credits_bank", "Créditos vigentes", "Número de créditos vigentes con el banco.", "numeric", "UCI Statlog German Credit Data", "Number of existing credits at this bank"),
    VariableDescriptor("job", "Tipo de empleo", "Clasificación laboral del solicitante.", "categorical", "UCI Statlog German Credit Data", "Job"),
    VariableDescriptor("liable_people", "Dependientes", "Número de personas a cargo.", "numeric", "UCI Statlog German Credit Data", "Number of people being liable to provide maintenance for"),
    VariableDescriptor("telephone", "Teléfono", "Disponibilidad de teléfono.", "categorical", "UCI Statlog German Credit Data", "Telephone"),
    VariableDescriptor("foreign_worker", "Trabajador extranjero", "Condición de trabajador extranjero.", "categorical", "UCI Statlog German Credit Data", "Foreign worker"),
]

DEFAULT_VARIABLES = [
    VariableDescriptor("LIMIT_BAL", "Cupo de crédito", "Monto del crédito otorgado.", "numeric", "Default Clients"),
    VariableDescriptor("SEX", "Sexo", "Sexo codificado del cliente.", "categorical", "Default Clients"),
    VariableDescriptor("EDUCATION", "Educación", "Nivel educativo codificado.", "categorical", "Default Clients"),
    VariableDescriptor("MARRIAGE", "Estado civil", "Estado civil codificado.", "categorical", "Default Clients"),
    VariableDescriptor("AGE", "Edad", "Edad del cliente.", "numeric", "Default Clients"),
    VariableDescriptor("PAY_0", "Mora reciente", "Estado de pago en el último periodo.", "numeric", "Default Clients"),
    VariableDescriptor("PAY_2", "Mora t-2", "Estado de pago dos periodos atrás.", "numeric", "Default Clients"),
    VariableDescriptor("PAY_3", "Mora t-3", "Estado de pago tres periodos atrás.", "numeric", "Default Clients"),
    VariableDescriptor("BILL_AMT1", "Factura reciente", "Monto facturado más reciente.", "numeric", "Default Clients"),
    VariableDescriptor("PAY_AMT1", "Pago reciente", "Pago más reciente realizado.", "numeric", "Default Clients"),
]


@dataclass
class DatasetBundle:
    exercise: str
    label: str
    df: pd.DataFrame
    features: list[str]
    target: str
    descriptors: list[VariableDescriptor]
    demo_mode: bool = False
    source_note: str = ""


class DatasetCatalog:
    def __init__(self) -> None:
        self.default_path = ROOT_DIR / "data" / "raw" / "Default_Clientes.csv"
        self.german_path = ROOT_DIR / "data" / "raw" / "statlog+german+credit+data" / "german.data"

    def load_default_risk(self) -> DatasetBundle:
        df = pd.read_csv(self.default_path, sep=";")
        df.columns = [column.strip() for column in df.columns]
        return DatasetBundle(
            exercise=ExerciseOption.DEFAULT_RISK,
            label=ExerciseOption.LABELS[ExerciseOption.DEFAULT_RISK],
            df=df,
            features=[column for column in df.columns if column not in {"ID", "Default"}],
            target="Default",
            descriptors=DEFAULT_VARIABLES,
            source_note="Dataset local disponible en data/raw/Default_Clientes.csv",
        )

    def load_credit_approval(self) -> DatasetBundle:
        columns = [descriptor.key for descriptor in GERMAN_VARIABLES] + ["credit_outcome"]
        df = pd.read_csv(self.german_path, sep=r"\s+", header=None)
        df.columns = columns
        return DatasetBundle(
            exercise=ExerciseOption.CREDIT_APPROVAL,
            label=ExerciseOption.LABELS[ExerciseOption.CREDIT_APPROVAL],
            df=df,
            features=columns[:-1],
            target="credit_outcome",
            descriptors=GERMAN_VARIABLES,
            source_note=(
                "Dataset oficial German Credit cargado desde data/raw/statlog+german+credit+data/german.data. "
                "El archivo german.data-numeric queda disponible como referencia técnica adicional."
            ),
        )

    def get_bundle(self, exercise: str) -> DatasetBundle:
        if exercise == ExerciseOption.CREDIT_APPROVAL:
            return self.load_credit_approval()
        return self.load_default_risk()


class ModelRegistry:
    def __init__(self, catalog: DatasetCatalog) -> None:
        self.catalog = catalog
        self._models: dict[str, tuple[Pipeline, DatasetBundle]] = {}

    def _build_pipeline(self, bundle: DatasetBundle) -> Pipeline:
        X = bundle.df[bundle.features]
        numeric_columns = X.select_dtypes(include=["number"]).columns.tolist()
        categorical_columns = [column for column in bundle.features if column not in numeric_columns]
        preprocessor = ColumnTransformer(
            transformers=[
                (
                    "num",
                    Pipeline(
                        steps=[
                            ("imputer", SimpleImputer(strategy="median")),
                            ("scaler", StandardScaler()),
                        ]
                    ),
                    numeric_columns,
                ),
                (
                    "cat",
                    Pipeline(
                        steps=[
                            ("imputer", SimpleImputer(strategy="most_frequent")),
                            ("encoder", OneHotEncoder(handle_unknown="ignore")),
                        ]
                    ),
                    categorical_columns,
                ),
            ]
        )
        model = Pipeline(
            steps=[
                ("preprocessor", preprocessor),
                ("classifier", LogisticRegression(max_iter=1000, random_state=42)),
            ]
        )
        model.fit(X, bundle.df[bundle.target])
        return model

    def get_model(self, exercise: str) -> tuple[Pipeline, DatasetBundle]:
        if exercise not in self._models:
            bundle = self.catalog.get_bundle(exercise)
            self._models[exercise] = (self._build_pipeline(bundle), bundle)
        return self._models[exercise]


class ExplainabilityService:
    def build_linear_explanations(
        self, pipeline: Pipeline, inputs: dict[str, Any]
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        preprocessor = pipeline.named_steps["preprocessor"]
        classifier = pipeline.named_steps["classifier"]
        transformed = preprocessor.transform(pd.DataFrame([inputs]))
        transformed_array = transformed.toarray() if hasattr(transformed, "toarray") else transformed
        contributions = np.ravel(transformed_array) * classifier.coef_[0]
        feature_names = preprocessor.get_feature_names_out()
        local = sorted(
            [
                {"feature": feature_names[index], "impact": float(value)}
                for index, value in enumerate(contributions)
            ],
            key=lambda item: abs(item["impact"]),
            reverse=True,
        )
        global_payload = sorted(
            [
                {"feature": feature_names[index], "importance": float(abs(value))}
                for index, value in enumerate(classifier.coef_[0])
            ],
            key=lambda item: item["importance"],
            reverse=True,
        )
        return (
            {"items": local[:10], "provider": "linear_shap_surrogate"},
            {"items": global_payload[:12], "provider": "coefficient_global_importance"},
        )


class PedagogicalExplanationAgent:
    def explain(
        self,
        exercise_label: str,
        prediction_label: str,
        probability: float,
        local_items: list[dict[str, Any]],
    ) -> str:
        top = ", ".join(
            f"{item['feature']} ({'aumenta' if item['impact'] >= 0 else 'reduce'} la probabilidad)"
            for item in local_items[:3]
        )
        return (
            f"En {exercise_label}, el modelo clasificó el caso como '{prediction_label}' "
            f"con una probabilidad estimada de {probability:.1%}. "
            f"Las variables con mayor peso local fueron {top}. "
            "La interpretación pedagógica es que el modelo compara el perfil actual con patrones históricos "
            "y usa esas señales para justificar la decisión."
        )


class PredictionService:
    def __init__(self, registry: ModelRegistry) -> None:
        self.registry = registry
        self.explainer = ExplainabilityService()
        self.agent = PedagogicalExplanationAgent()

    def predict(self, exercise: str, features: dict[str, Any]) -> PredictionResult:
        pipeline, bundle = self.registry.get_model(exercise)
        probability = float(pipeline.predict_proba(pd.DataFrame([features]))[0, 1])
        if exercise == ExerciseOption.CREDIT_APPROVAL:
            label = "Aprobado" if probability >= 0.5 else "Requiere revisión"
        else:
            label = "Alta probabilidad de mora" if probability >= 0.5 else "Baja probabilidad de mora"
        local, global_payload = self.explainer.build_linear_explanations(pipeline, features)
        summary = self.agent.explain(bundle.label, label, probability, local["items"])
        return PredictionResult(
            exercise=exercise,
            probability=probability,
            label=label,
            features=features,
            provider="logistic_regression",
            local_explanations={
                "lime": {"items": local["items"], "provider": "local_surrogate"},
                "shap_local": local,
            },
            global_explanations={"shap_global": global_payload},
            pedagogical_summary=summary,
        )
