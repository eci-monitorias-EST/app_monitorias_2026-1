from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import shap
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, precision_score, recall_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.tree import DecisionTreeClassifier

from domain.models import ExerciseOption, ModelEvaluationResult, PredictionResult, VariableDescriptor


ROOT_DIR = Path(__file__).resolve().parents[2]


GERMAN_VARIABLES = [
    VariableDescriptor("duration_months", "Duración del crédito", "Número de meses pactados para pagar el crédito solicitado.", "numeric", "UCI Statlog German Credit Data", "Duration in month"),
    VariableDescriptor("credit_amount", "Monto del crédito", "Valor total del crédito solicitado por el cliente.", "numeric", "UCI Statlog German Credit Data", "Credit amount"),
    VariableDescriptor("installment_rate", "Tasa de cuota", "Cuota como porcentaje del ingreso disponible.", "numeric", "UCI Statlog German Credit Data", "Installment rate in percentage of disposable income"),
    VariableDescriptor("existing_credits", "Créditos vigentes", "Número de créditos vigentes con el banco.", "numeric", "UCI Statlog German Credit Data", "Number of existing credits at this bank"),
    VariableDescriptor("status_checking_account", "Cuenta corriente", "Estado de la cuenta corriente del solicitante.", "categorical", "UCI Statlog German Credit Data", "Status of existing checking account"),
    VariableDescriptor("credit_history_grouped", "Historial crediticio agrupado", "Historial crediticio agrupado según experiencia crediticia previa.", "categorical", "UCI Statlog German Credit Data", "Grouped credit history"),
    VariableDescriptor("savings_account", "Ahorros / bonos", "Nivel de ahorro o bonos declarados.", "categorical", "UCI Statlog German Credit Data", "Savings account/bonds"),
    VariableDescriptor("other_debtors", "Otros deudores", "Existencia de codeudores o garantes.", "categorical", "UCI Statlog German Credit Data", "Other debtors / guarantors"),
    VariableDescriptor("property", "Tipo de propiedad", "Tipo de activo o propiedad declarada.", "categorical", "UCI Statlog German Credit Data", "Property"),
    VariableDescriptor("other_installment_plans", "Otros planes de pago", "Existencia de otros planes de pago.", "categorical", "UCI Statlog German Credit Data", "Other installment plans"),
    VariableDescriptor("housing", "Vivienda", "Situación de vivienda del solicitante.", "categorical", "UCI Statlog German Credit Data", "Housing"),
    VariableDescriptor("job", "Tipo de empleo", "Clasificación laboral del solicitante.", "categorical", "UCI Statlog German Credit Data", "Job"),
    VariableDescriptor("employment_agroup", "Antigüedad laboral agrupada", "Antigüedad laboral segmentada según experiencia en el empleo.", "categorical", "UCI Statlog German Credit Data", "Employment group"),
]

DEFAULT_VARIABLES = [
    VariableDescriptor("LIMIT_BAL", "Cupo de crédito", "Monto máximo de crédito asignado al cliente.", "numeric", "Default Clients"),
    VariableDescriptor("SEX", "Sexo", "Sexo codificado del cliente.", "categorical", "Default Clients"),
    VariableDescriptor("EDUCATION", "Nivel educativo", "Nivel de educación reportado para el cliente.", "categorical", "Default Clients"),
    VariableDescriptor("MARRIAGE", "Estado civil", "Situación familiar o estado civil del cliente.", "categorical", "Default Clients"),
    VariableDescriptor("PAY_max", "Mayor retraso de pago", "Máximo estado de pago atrasado en los periodos recientes.", "numeric", "Default Clients"),
    VariableDescriptor("PAY_mean", "Promedio de retrasos", "Promedio de los estados de pago atrasado entre los periodos recientes.", "numeric", "Default Clients"),
    VariableDescriptor("PAY_n_atrasos", "Número de atrasos", "Número de periodos con pago atrasado.", "numeric", "Default Clients"),
    VariableDescriptor("PAY_AMT_total", "Total pagado", "Suma de los pagos realizados en los últimos periodos.", "numeric", "Default Clients"),
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
        self.german_path = ROOT_DIR / "data" / "raw" / "statlog+german+credit+data" / "german.data-numeric"

    def load_default_risk(self) -> DatasetBundle:
        df = pd.read_csv(self.default_path, sep=';')
        df.columns = [column.strip() for column in df.columns]

        pay_cols = ['PAY_0', 'PAY_2', 'PAY_3', 'PAY_4', 'PAY_5', 'PAY_6']
        pay_amt_cols = ['PAY_AMT1', 'PAY_AMT2', 'PAY_AMT3', 'PAY_AMT4', 'PAY_AMT5', 'PAY_AMT6']

        # Ingeniería de variables según modelo seleccionado en notebooks/modelo_mora_seleecionado.py
        df['PAY_max'] = df[pay_cols].max(axis=1)
        df['PAY_mean'] = df[pay_cols].mean(axis=1)
        df['PAY_n_atrasos'] = (df[pay_cols] > 0).sum(axis=1)
        df['PAY_AMT_total'] = df[pay_amt_cols].sum(axis=1)

        descriptor_keys = [
            'LIMIT_BAL',
            'SEX',
            'EDUCATION',
            'MARRIAGE',
            'PAY_max',
            'PAY_mean',
            'PAY_n_atrasos',
            'PAY_AMT_total',
        ]
        df = df[descriptor_keys + ['Default']]

        return DatasetBundle(
            exercise=ExerciseOption.DEFAULT_RISK,
            label=ExerciseOption.LABELS[ExerciseOption.DEFAULT_RISK],
            df=df,
            features=descriptor_keys,
            target='Default',
            descriptors=DEFAULT_VARIABLES,
            source_note='Dataset local disponible en data/raw/Default_Clientes.csv con ingeniería de características del modelo seleccionado.',
        )

    def load_credit_approval(self) -> DatasetBundle:
        df = pd.read_csv(self.german_path, sep=r"\s+", header=None)
        all_feature_names = [
            'status_checking_account',
            'duration_months',
            'credit_history',
            'purpose',
            'credit_amount',
            'savings_account',
            'employment_since',
            'installment_rate',
            'personal_status_sex',
            'other_debtors',
            'present_residence',
            'property',
            'age_years',
            'other_installment_plans',
            'housing',
            'existing_credits',
            'job',
            'liable_people',
            'telephone',
            'foreign_worker',
        ]
        extra_columns = [f'binarized_{i}' for i in range(1, 5)]
        df.columns = all_feature_names[:20] + extra_columns + ['target']

        df['credit_history_grouped'] = df['credit_history'].apply(
            lambda x: 0 if x in [1, 2, 3] else 1 if x == 4 else 2
        )
        df['employment_agroup'] = df['employment_since'].apply(
            lambda x: 0 if x == 1 else 1 if x in [2, 3] else 2
        )
        df['target'] = df['target'].map({1: 0, 2: 1})
        df['credit_outcome'] = df['target']

        feature_keys = [
            'duration_months',
            'credit_amount',
            'installment_rate',
            'existing_credits',
            'status_checking_account',
            'credit_history_grouped',
            'savings_account',
            'other_debtors',
            'property',
            'other_installment_plans',
            'housing',
            'job',
            'employment_agroup',
        ]

        return DatasetBundle(
            exercise=ExerciseOption.CREDIT_APPROVAL,
            label=ExerciseOption.LABELS[ExerciseOption.CREDIT_APPROVAL],
            df=df,
            features=feature_keys,
            target='target',
            descriptors=GERMAN_VARIABLES,
            source_note='Dataset German Credit cargado desde data/raw/statlog+german+credit+data/german.data-numeric con ingeniería de características del modelo seleccionado.',
        )

    def get_bundle(self, exercise: str) -> DatasetBundle:
        if exercise == ExerciseOption.CREDIT_APPROVAL:
            return self.load_credit_approval()
        return self.load_default_risk()


def build_preprocessor(bundle: DatasetBundle) -> ColumnTransformer:
    X = bundle.df[bundle.features]
    numeric_columns = X.select_dtypes(include=["number"]).columns.tolist()
    categorical_columns = [column for column in bundle.features if column not in numeric_columns]
    return ColumnTransformer(
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


class ModelRegistry:
    def __init__(self, catalog: DatasetCatalog) -> None:
        self.catalog = catalog
        self._models: dict[str, tuple[Pipeline, DatasetBundle]] = {}

    def _build_pipeline(self, bundle: DatasetBundle) -> Pipeline:
        classifier = (
            DecisionTreeClassifier(
                max_depth=6,
                min_samples_leaf=27,
                min_samples_split=13,
                criterion="entropy",
                class_weight="balanced",
                random_state=42,
            )
            if bundle.exercise == ExerciseOption.DEFAULT_RISK
            else LogisticRegression(max_iter=1000, random_state=42)
        )
        model = Pipeline(
            steps=[
                ("preprocessor", build_preprocessor(bundle)),
                ("classifier", classifier),
            ]
        )
        model.fit(bundle.df[bundle.features], bundle.df[bundle.target])
        return model

    def get_model(self, exercise: str) -> tuple[Pipeline, DatasetBundle]:
        if exercise not in self._models:
            bundle = self.catalog.get_bundle(exercise)
            self._models[exercise] = (self._build_pipeline(bundle), bundle)
        return self._models[exercise]


EVALUATION_CLASS_LABELS = {
    ExerciseOption.CREDIT_APPROVAL: ("Requiere revisión", "Aprobado"),
    ExerciseOption.DEFAULT_RISK: ("Sin mora", "Mora"),
}

EVALUATION_MODEL_NAMES = {
    ExerciseOption.CREDIT_APPROVAL: "Regresión logística",
    ExerciseOption.DEFAULT_RISK: "Árbol de decisión",
}


def _positive_class_shap_values(shap_values: Any) -> np.ndarray:
    """Normaliza la salida de SHAP (lista por clase o array 3D) a un array 2D (muestras x variables) de la clase positiva."""
    if isinstance(shap_values, list):
        return np.asarray(shap_values[1] if len(shap_values) > 1 else shap_values[0])
    array = np.asarray(shap_values)
    if array.ndim == 3:
        return array[:, :, 1] if array.shape[2] > 1 else array[:, :, 0]
    return array


class ModelEvaluationService:
    """Evalúa, sobre un split de prueba, el modelo seleccionado en los notebooks de cada ejercicio
    (notebooks/modelo_credito.py y notebooks/modelo_mora_seleecionado.py)."""

    def __init__(self, catalog: DatasetCatalog) -> None:
        self.catalog = catalog
        self._cache: dict[str, ModelEvaluationResult] = {}

    @staticmethod
    def _build_classifier(exercise: str) -> BaseEstimator:
        if exercise == ExerciseOption.DEFAULT_RISK:
            return DecisionTreeClassifier(
                max_depth=6,
                min_samples_leaf=27,
                min_samples_split=13,
                criterion="entropy",
                class_weight="balanced",
                random_state=42,
            )
        return LogisticRegression(max_iter=1000, random_state=42, class_weight="balanced")

    def evaluate(self, exercise: str) -> ModelEvaluationResult:
        if exercise not in self._cache:
            self._cache[exercise] = self._evaluate(exercise)
        return self._cache[exercise]

    def _evaluate(self, exercise: str) -> ModelEvaluationResult:
        bundle = self.catalog.get_bundle(exercise)
        X = bundle.df[bundle.features]
        y = bundle.df[bundle.target]
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, stratify=y, random_state=42
        )

        preprocessor = build_preprocessor(bundle)
        classifier = self._build_classifier(exercise)
        pipeline = Pipeline(steps=[("preprocessor", preprocessor), ("classifier", classifier)])
        pipeline.fit(X_train, y_train)
        y_pred = pipeline.predict(X_test)

        feature_names = [
            name.split("__", 1)[-1] for name in preprocessor.get_feature_names_out().tolist()
        ]
        transformed_test = preprocessor.transform(X_test)
        transformed_test = (
            transformed_test.toarray() if hasattr(transformed_test, "toarray") else transformed_test
        )

        if isinstance(classifier, DecisionTreeClassifier):
            explainer = shap.TreeExplainer(classifier)
            shap_values = explainer.shap_values(transformed_test)
        else:
            transformed_train = preprocessor.transform(X_train)
            transformed_train = (
                transformed_train.toarray() if hasattr(transformed_train, "toarray") else transformed_train
            )
            explainer = shap.LinearExplainer(
                classifier, transformed_train, feature_perturbation="interventional"
            )
            shap_values = explainer.shap_values(transformed_test)

        mean_abs_shap = np.abs(_positive_class_shap_values(shap_values)).mean(axis=0)
        shap_importance = sorted(
            (
                {"feature": name, "importance": float(value)}
                for name, value in zip(feature_names, mean_abs_shap)
            ),
            key=lambda item: item["importance"],
            reverse=True,
        )[:10]

        return ModelEvaluationResult(
            exercise=exercise,
            model_name=EVALUATION_MODEL_NAMES[exercise],
            accuracy=float(accuracy_score(y_test, y_pred)),
            precision=float(precision_score(y_test, y_pred, zero_division=0)),
            recall=float(recall_score(y_test, y_pred, zero_division=0)),
            f1=float(f1_score(y_test, y_pred, zero_division=0)),
            confusion_matrix=confusion_matrix(y_test, y_pred).tolist(),
            class_labels=EVALUATION_CLASS_LABELS[exercise],
            shap_importance=shap_importance,
            test_size=len(y_test),
        )


class ExplainabilityService:
    def _transform_inputs(
        self, pipeline: Pipeline, inputs: dict[str, Any]
    ) -> tuple[pd.DataFrame, np.ndarray, list[str]]:
        preprocessor = pipeline.named_steps["preprocessor"]
        transformed = preprocessor.transform(pd.DataFrame([inputs]))
        feature_names = preprocessor.get_feature_names_out().tolist()
        transformed_array = transformed.toarray() if hasattr(transformed, "toarray") else transformed
        transformed_df = pd.DataFrame(transformed_array, columns=feature_names)
        return transformed_df, transformed_array, feature_names

    def build_explanations(
        self, pipeline: Pipeline, inputs: dict[str, Any]
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        classifier = pipeline.named_steps["classifier"]
        transformed_df, transformed_array, feature_names = self._transform_inputs(pipeline, inputs)

        if isinstance(classifier, DecisionTreeClassifier):
            try:
                explainer = shap.TreeExplainer(classifier)
                shap_values = explainer.shap_values(transformed_df)
                if isinstance(shap_values, list):
                    if len(shap_values) > 1:
                        shap_values = shap_values[1]
                    elif len(shap_values) == 1:
                        shap_values = shap_values[0]
                    else:
                        shap_values = np.zeros((1, len(feature_names)))
                shap_array = np.ravel(shap_values)
                slice_count = min(len(feature_names), shap_array.size)
                shap_array = shap_array[:slice_count]
                feature_names = feature_names[:slice_count]
            except Exception:
                shap_array = np.ravel(transformed_array) * classifier.feature_importances_
                slice_count = min(len(feature_names), shap_array.size)
                shap_array = shap_array[:slice_count]
                feature_names = feature_names[:slice_count]

            local = sorted(
                [
                    {"feature": feature, "impact": float(value)}
                    for feature, value in zip(feature_names, shap_array)
                ],
                key=lambda item: abs(item["impact"]),
                reverse=True,
            )
            global_payload = sorted(
                [
                    {"feature": name, "importance": float(abs(value))}
                    for name, value in zip(feature_names, classifier.feature_importances_)
                ],
                key=lambda item: item["importance"],
                reverse=True,
            )
            return (
                {"items": local[:10], "provider": "shap_tree_local"},
                {"items": global_payload[:12], "provider": "feature_importance"},
            )

        transformed_array = transformed_array if isinstance(transformed_array, np.ndarray) else np.array(transformed_array)
        contributions = np.ravel(transformed_array) * classifier.coef_[0]
        local = sorted(
            [
                {"feature": feature, "impact": float(value)}
                for feature, value in zip(feature_names, contributions)
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

    @staticmethod
    def _positive_class_for_exercise(exercise: str) -> int:
        positive_classes = {
            ExerciseOption.CREDIT_APPROVAL: 1,
            ExerciseOption.DEFAULT_RISK: 1,
        }
        return positive_classes[exercise]

    def _positive_class_probability(self, pipeline: Pipeline, exercise: str, features: dict[str, Any]) -> float:
        classes = list(pipeline.named_steps["classifier"].classes_)
        positive_class = self._positive_class_for_exercise(exercise)
        if positive_class not in classes:
            raise ValueError(
                f"Positive class {positive_class!r} is not available for exercise {exercise!r}."
            )
        positive_index = classes.index(positive_class)
        probabilities = pipeline.predict_proba(pd.DataFrame([features]))[0]
        return float(probabilities[positive_index])

    def predict(self, exercise: str, features: dict[str, Any]) -> PredictionResult:
        pipeline, bundle = self.registry.get_model(exercise)
        probability = self._positive_class_probability(pipeline, exercise, features)
        classifier = pipeline.named_steps["classifier"]
        if exercise == ExerciseOption.CREDIT_APPROVAL:
            label = "Aprobado" if probability >= 0.5 else "Requiere revisión"
        else:
            label = "Alta probabilidad de mora" if probability >= 0.5 else "Baja probabilidad de mora"
        local, global_payload = self.explainer.build_explanations(pipeline, features)
        summary = self.agent.explain(bundle.label, label, probability, local["items"])
        provider = (
            "decision_tree"
            if isinstance(classifier, DecisionTreeClassifier)
            else "logistic_regression"
        )
        return PredictionResult(
            exercise=exercise,
            probability=probability,
            label=label,
            features=features,
            provider=provider,
            local_explanations={
                "lime": {"items": local["items"], "provider": "local_surrogate"},
                "shap_local": local,
            },
            global_explanations={"shap_global": global_payload},
            pedagogical_summary=summary,
        )
