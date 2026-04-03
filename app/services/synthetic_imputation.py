from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

import numpy as np
import pandas as pd
import plotly.express as px

from domain.models import CompletedComment, PredictionResult


LOGGER = logging.getLogger(__name__)
SYNTHETIC_MARKER = "DATOS_SINTETICOS"
SYNTHETIC_ORIGIN = "synthetic_mass_imputation"


class ScenarioFeatureResolver(Protocol):
    def resolve_features(self, exercise: str, dataset_row_index: int) -> dict[str, Any]:
        ...


class ExercisePredictor(Protocol):
    def predict(self, exercise: str, features: dict[str, Any]) -> PredictionResult:
        ...


@dataclass(frozen=True)
class SyntheticFeedbackSpec:
    rating: int
    summary: str
    missing_topics: str
    improvement_ideas: str


@dataclass(frozen=True)
class SyntheticScenarioSpec:
    scenario_id: str
    exercise: str
    dataset_row_index: int
    profile: dict[str, Any]
    dataset_comment: str
    analytics_comment: str
    prediction_reflection: str
    feedback: SyntheticFeedbackSpec


@dataclass(frozen=True)
class SyntheticSeedRecord:
    scenario_id: str
    participant_id: str
    public_alias: str
    exercise: str
    profile: dict[str, Any]
    progress_payload: dict[str, Any]
    feedback_payload: dict[str, Any]
    traceability_payload: dict[str, Any]


@dataclass(frozen=True)
class SyntheticBatch:
    test_batch_id: str
    records: list[SyntheticSeedRecord]

    @property
    def total_records(self) -> int:
        return len(self.records)

    @property
    def exercises(self) -> tuple[str, ...]:
        return tuple(sorted({record.exercise for record in self.records}))


class DatasetCatalogFeatureResolver:
    def __init__(self, catalog: Any) -> None:
        self.catalog = catalog
        self._bundle_cache: dict[str, Any] = {}

    def resolve_features(self, exercise: str, dataset_row_index: int) -> dict[str, Any]:
        bundle = self._bundle_cache.get(exercise)
        if bundle is None:
            bundle = self.catalog.get_bundle(exercise)
            self._bundle_cache[exercise] = bundle

        if dataset_row_index < 0 or dataset_row_index >= len(bundle.df.index):
            raise IndexError(
                f"dataset_row_index={dataset_row_index} fuera de rango para exercise={exercise!r}"
            )

        row = bundle.df.iloc[dataset_row_index][bundle.features].to_dict()
        return {key: _to_python_value(value) for key, value in row.items()}


class SyntheticBatchBuilder:
    def __init__(
        self,
        *,
        feature_resolver: ScenarioFeatureResolver,
        predictor: ExercisePredictor,
        origin_label: str = SYNTHETIC_ORIGIN,
    ) -> None:
        self.feature_resolver = feature_resolver
        self.predictor = predictor
        self.origin_label = origin_label

    def build_batch(
        self,
        scenarios: list[SyntheticScenarioSpec],
        *,
        test_batch_id: str,
    ) -> SyntheticBatch:
        records: list[SyntheticSeedRecord] = []
        for index, scenario in enumerate(scenarios, start=1):
            participant_id = f"synthetic-{test_batch_id}-{index:03d}"
            public_alias = f"TEST-{index:03d}"
            prediction_inputs = self.feature_resolver.resolve_features(
                scenario.exercise,
                scenario.dataset_row_index,
            )
            prediction_output = self.predictor.predict(
                scenario.exercise,
                prediction_inputs,
            ).to_dict()

            traceability_payload = {
                "is_test_data": True,
                "test_batch_id": test_batch_id,
                "data_origin": self.origin_label,
            }

            records.append(
                SyntheticSeedRecord(
                    scenario_id=scenario.scenario_id,
                    participant_id=participant_id,
                    public_alias=public_alias,
                    exercise=scenario.exercise,
                    profile=_build_synthetic_profile(scenario.profile),
                    progress_payload={
                        "dataset_comment": _tag_text(scenario.dataset_comment, test_batch_id),
                        "analytics_comment": _tag_text(scenario.analytics_comment, test_batch_id),
                        "prediction_reflection": _tag_text(
                            scenario.prediction_reflection,
                            test_batch_id,
                        ),
                        "prediction_inputs": prediction_inputs,
                        "prediction_output": prediction_output,
                    },
                    feedback_payload={
                        "rating": scenario.feedback.rating,
                        "summary": _tag_text(scenario.feedback.summary, test_batch_id),
                        "missing_topics": _tag_text(
                            scenario.feedback.missing_topics,
                            test_batch_id,
                        ),
                        "improvement_ideas": _tag_text(
                            scenario.feedback.improvement_ideas,
                            test_batch_id,
                        ),
                    },
                    traceability_payload=traceability_payload,
                )
            )

        LOGGER.info(
            "Synthetic batch built successfully.",
            extra={
                "test_batch_id": test_batch_id,
                "records": len(records),
                "exercises": sorted({record.exercise for record in records}),
            },
        )
        return SyntheticBatch(test_batch_id=test_batch_id, records=records)


def load_synthetic_scenarios(path: Path) -> list[SyntheticScenarioSpec]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    raw_scenarios = payload.get("participants", [])
    scenarios: list[SyntheticScenarioSpec] = []
    for raw in raw_scenarios:
        feedback_payload = raw.get("feedback", {})
        scenarios.append(
            SyntheticScenarioSpec(
                scenario_id=str(raw["scenario_id"]),
                exercise=str(raw["exercise"]),
                dataset_row_index=int(raw["dataset_row_index"]),
                profile=dict(raw.get("profile", {})),
                dataset_comment=str(raw.get("dataset_comment", "")),
                analytics_comment=str(raw.get("analytics_comment", "")),
                prediction_reflection=str(raw.get("prediction_reflection", "")),
                feedback=SyntheticFeedbackSpec(
                    rating=int(feedback_payload.get("rating", 0)),
                    summary=str(feedback_payload.get("summary", "")),
                    missing_topics=str(feedback_payload.get("missing_topics", "")),
                    improvement_ideas=str(feedback_payload.get("improvement_ideas", "")),
                ),
            )
        )
    return scenarios


def build_projection_comments(
    batch_payload: dict[str, Any],
    *,
    exercise: str,
) -> list[CompletedComment]:
    sessions_by_participant = {
        str(row.get("participant_id", "")).strip(): row
        for row in batch_payload.get("sesiones", [])
    }
    comments: list[CompletedComment] = []
    for row in batch_payload.get("respuestas", []):
        if str(row.get("exercise", "")).strip() != exercise:
            continue

        participant_id = str(row.get("participant_id", "")).strip()
        combined_comment = " ".join(
            [
                str(row.get("dataset_comment", "")).strip(),
                str(row.get("analytics_comment", "")).strip(),
                str(row.get("prediction_reflection", "")).strip(),
            ]
        ).strip()
        if not combined_comment:
            continue

        session_row = sessions_by_participant.get(participant_id, {})
        comments.append(
            CompletedComment(
                participant_id=participant_id,
                public_alias=str(session_row.get("public_alias", participant_id)).strip() or participant_id,
                exercise=exercise,
                combined_comment=combined_comment,
                current_user=False,
            )
        )
    return comments


def export_projection_html(
    projection: dict[str, Any],
    *,
    output_path: Path,
    title: str,
    test_batch_id: str,
    exercise: str,
) -> Path:
    points = projection.get("points", [])
    if not points:
        raise ValueError("No hay puntos para exportar en la proyección 3D.")

    dataframe = pd.DataFrame(points)
    figure = px.scatter_3d(
        dataframe,
        x="x",
        y="y",
        z="z",
        color="public_alias",
        hover_name="public_alias",
        hover_data={
            "participant_id": True,
            "comment": True,
            "clean_comment": True,
            "x": ":.3f",
            "y": ":.3f",
            "z": ":.3f",
        },
        title=title,
    )
    figure.update_traces(marker={"size": 6, "opacity": 0.85})
    figure.update_layout(
        scene={
            "xaxis_title": "UMAP/PCA X",
            "yaxis_title": "UMAP/PCA Y",
            "zaxis_title": "UMAP/PCA Z",
        },
        legend_title_text="Alias sintético",
        margin={"l": 0, "r": 0, "b": 0, "t": 60},
        annotations=[
            {
                "text": (
                    f"Lote: {test_batch_id} | Ejercicio: {exercise} | "
                    f"Embeddings: {projection.get('embedding_provider', 'n/a')} | "
                    f"Reducción: {projection.get('reduction_provider', 'n/a')}"
                ),
                "xref": "paper",
                "yref": "paper",
                "x": 0,
                "y": 1.05,
                "showarrow": False,
            }
        ],
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    figure.write_html(str(output_path), include_plotlyjs="cdn", full_html=True)
    return output_path


def build_delete_batch_payload(test_batch_id: str, *, dry_run: bool) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "test_batch_id": test_batch_id,
        "dry_run": dry_run,
    }
    if not dry_run:
        payload["confirm_phrase"] = "DELETE_TEST_BATCH"
    return payload


def _build_synthetic_profile(profile: dict[str, Any]) -> dict[str, Any]:
    output = {key: _to_python_value(value) for key, value in profile.items()}
    name = str(output.get("nombre", "Participante Sintético")).strip()
    school = str(output.get("colegio", "Colegio Sintético")).strip()
    output["nombre"] = name if name.upper().startswith("SINTÉTICO") else f"SINTÉTICO {name}"
    output["colegio"] = school if "sintétic" in school.lower() else f"{school} (sintético)"
    return output


def _tag_text(text: str, test_batch_id: str) -> str:
    cleaned = str(text).strip()
    marker = f"[{SYNTHETIC_MARKER}|batch={test_batch_id}]"
    if not cleaned:
        return marker
    if cleaned.startswith(marker):
        return cleaned
    return f"{marker} {cleaned}"


def _to_python_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _to_python_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_to_python_value(item) for item in value]
    if isinstance(value, tuple):
        return [_to_python_value(item) for item in value]
    if isinstance(value, np.generic):
        return value.item()
    if pd.isna(value):
        return None
    return value
