from __future__ import annotations

import sys
from types import ModuleType
from typing import Any

import numpy as np
import pytest

from domain.models import CompletedComment
from services.embedding_providers import ConfigurableEmbeddingProvider, EmbeddingResult
from services.text_pipeline import (
    CommentAnalyticsService,
    DimensionalityReducer,
    TextCleaner,
    build_comment_hash,
)


class _EmbedderStub:
    def __init__(self, provider: str = "sentence_transformers_minilm") -> None:
        self.provider = provider

    def encode(self, texts: list[str]) -> EmbeddingResult:
        del texts
        return EmbeddingResult(
            matrix=np.array([[0.1, 0.2, 0.3], [0.3, 0.2, 0.1]]),
            provider=self.provider,
        )


class _ReducerStub:
    def reduce(self, matrix: np.ndarray) -> tuple[np.ndarray, str]:
        del matrix
        return np.array([[1.0, 2.0, 3.0], [3.0, 2.0, 1.0]]), "umap"


class _ReducerSingleStub:
    def reduce(self, matrix: np.ndarray) -> tuple[np.ndarray, str]:
        del matrix
        return np.array([[9.0, 8.0, 7.0]]), "umap"


class _RemoteSyncStub:
    def __init__(
        self,
        *,
        comment_events: list[dict[str, Any]] | None = None,
        embedding_rows: list[dict[str, Any]] | None = None,
        projection_rows: list[dict[str, Any]] | None = None,
    ) -> None:
        self.comment_events = comment_events
        self.embedding_rows = embedding_rows
        self.projection_rows = projection_rows
        self.saved_embeddings: list[dict[str, Any]] = []
        self.saved_projections: list[dict[str, Any]] = []

    def query_comment_events(self, exercise: str, limit_rows: int) -> list[dict[str, Any]] | None:
        del limit_rows
        if self.comment_events is None:
            return None
        return [row for row in self.comment_events if row["exercise"] == exercise]

    def query_embeddings_cache(
        self,
        *,
        exercise: str,
        embedding_version: str,
        comment_hashes: list[str],
    ) -> list[dict[str, Any]] | None:
        del embedding_version
        if self.embedding_rows is None:
            return None
        return [
            row
            for row in self.embedding_rows
            if row["exercise"] == exercise
            and row["comment_hash"] in comment_hashes
        ]

    def upsert_embeddings_cache(self, rows: list[dict[str, Any]]) -> None:
        self.saved_embeddings.extend(rows)

    def query_projection_cache(
        self,
        *,
        exercise: str,
        projection_version: str,
        comment_hashes: list[str],
    ) -> list[dict[str, Any]] | None:
        del projection_version
        if self.projection_rows is None:
            return None
        return [
            row
            for row in self.projection_rows
            if row["exercise"] == exercise
            and row["comment_hash"] in comment_hashes
        ]

    def upsert_projection_cache(self, rows: list[dict[str, Any]]) -> None:
        self.saved_projections.extend(rows)


class _SinglePointEmbedderStub:
    def encode(self, texts: list[str]) -> EmbeddingResult:
        del texts
        return EmbeddingResult(
            matrix=np.array([[0.5, 0.1, 0.9]]),
            provider="sentence_transformers_minilm",
        )


class _ThreePointEmbedderStub:
    def encode(self, texts: list[str]) -> EmbeddingResult:
        del texts
        return EmbeddingResult(
            matrix=np.array(
                [
                    [0.1, 0.2, 0.3, 0.4],
                    [0.4, 0.1, 0.2, 0.5],
                    [0.3, 0.6, 0.1, 0.2],
                ]
            ),
            provider="sentence_transformers_minilm",
        )


class _FourPointEmbedderStub:
    def encode(self, texts: list[str]) -> EmbeddingResult:
        del texts
        return EmbeddingResult(
            matrix=np.array(
                [
                    [0.1, 0.2, 0.3, 0.4],
                    [0.4, 0.1, 0.2, 0.5],
                    [0.3, 0.6, 0.1, 0.2],
                    [0.5, 0.4, 0.2, 0.1],
                ]
            ),
            provider="sentence_transformers_minilm",
        )


def test_cleaner_removes_noise() -> None:
    cleaner = TextCleaner()
    cleaned = cleaner.clean("¡Visité https://bankify.test y EL modelo fue MUY claro!")
    assert "https" not in cleaned
    assert "muy" not in cleaned
    assert "modelo" in cleaned


def test_build_comment_hash_is_stable_for_equivalent_text() -> None:
    first = build_comment_hash("¡El modelo fue MUY claro! https://bankify.test")
    second = build_comment_hash("El modelo fue claro")

    assert first == second


def test_projection_builds_3d_points() -> None:
    service = CommentAnalyticsService(embedder=_EmbedderStub(), reducer=_ReducerStub())
    projection = service.build_projection(
        [
            CompletedComment("a1", "P-001", "default_risk", "El dashboard mostró mora alta", True),
            CompletedComment("a2", "P-002", "default_risk", "La edad y el atraso explican el riesgo", False),
        ]
    )
    assert len(projection["points"]) == 2
    assert projection["points"][0]["x"] == 1.0
    assert projection["embedding_provider"] == "sentence_transformers_minilm"


def test_projection_uses_minilm_provider_when_configured() -> None:
    service = CommentAnalyticsService(embedder=_EmbedderStub(), reducer=_ReducerStub())

    projection = service.build_projection(
        [
            CompletedComment("a1", "P-001", "default_risk", "El dashboard mostró mora alta", True),
            CompletedComment("a2", "P-002", "default_risk", "La edad y el atraso explican el riesgo", False),
        ]
    )

    assert projection["embedding_provider"] == "sentence_transformers_minilm"
    assert projection["reduction_provider"] == "umap"


def test_projection_returns_origin_for_single_point() -> None:
    service = CommentAnalyticsService(embedder=_SinglePointEmbedderStub(), reducer=DimensionalityReducer())

    projection = service.build_projection(
        [
            CompletedComment(
                "a1",
                "P-001",
                "default_risk",
                "Solo había un comentario disponible",
                True,
            )
        ]
    )

    assert projection["reduction_provider"] == "single_point"
    assert projection["points"] == [
        {
            "participant_id": "a1",
            "public_alias": "P-001",
            "comment": "Solo había un comentario disponible",
            "clean_comment": "solo habia comentario disponible",
            "comment_hash": build_comment_hash("solo habia comentario disponible", is_clean=True),
            "x": 0.0,
            "y": 0.0,
            "z": 0.0,
            "current_user": True,
            "comment_type": "",
            "comment_type_label": "",
        }
    ]


def test_projection_uses_small_sample_fallback_for_three_points() -> None:
    service = CommentAnalyticsService(embedder=_ThreePointEmbedderStub(), reducer=DimensionalityReducer())

    projection = service.build_projection(
        [
            CompletedComment("a1", "P-001", "default_risk", "Comentario uno", True),
            CompletedComment("a2", "P-002", "default_risk", "Comentario dos", False),
            CompletedComment("a3", "P-003", "default_risk", "Comentario tres", False),
        ]
    )

    assert projection["reduction_provider"] == "small_sample_fallback"
    assert len(projection["points"]) == 3
    for point in projection["points"]:
        assert {"x", "y", "z"}.issubset(point)
        assert all(np.isfinite(point[axis]) for axis in ("x", "y", "z"))


def test_projection_uses_small_sample_fallback_for_four_points() -> None:
    service = CommentAnalyticsService(embedder=_FourPointEmbedderStub(), reducer=DimensionalityReducer())

    projection = service.build_projection(
        [
            CompletedComment("a1", "P-001", "default_risk", "Comentario uno", True),
            CompletedComment("a2", "P-002", "default_risk", "Comentario dos", False),
            CompletedComment("a3", "P-003", "default_risk", "Comentario tres", False),
            CompletedComment("a4", "P-004", "default_risk", "Comentario cuatro", False),
        ]
    )

    assert projection["reduction_provider"] == "small_sample_fallback"
    assert len(projection["points"]) == 4
    for point in projection["points"]:
        assert {"x", "y", "z"}.issubset(point)
        assert all(np.isfinite(point[axis]) for axis in ("x", "y", "z"))


def test_reducer_uses_umap_for_normal_sample_sizes(monkeypatch: pytest.MonkeyPatch) -> None:
    reducer = DimensionalityReducer()
    matrix = np.array(
        [
            [0.1, 0.0, 0.2],
            [0.0, 0.2, 0.1],
            [0.3, 0.1, 0.0],
            [0.2, 0.4, 0.3],
            [0.4, 0.3, 0.2],
        ]
    )

    fake_module = ModuleType("umap")

    class _FakeUMAP:
        def __init__(self, *, n_components: int, n_neighbors: int, random_state: int) -> None:
            assert n_components == 3
            assert n_neighbors == 4
            assert random_state == 42

        def fit_transform(self, received_matrix: np.ndarray) -> np.ndarray:
            assert np.array_equal(received_matrix, matrix)
            return np.array(
                [
                    [1.0, 0.0, 0.0],
                    [0.0, 1.0, 0.0],
                    [0.0, 0.0, 1.0],
                    [1.0, 1.0, 1.0],
                    [0.5, 0.5, 0.5],
                ]
            )

    setattr(fake_module, "UMAP", _FakeUMAP)
    monkeypatch.setitem(sys.modules, "umap", fake_module)

    coordinates, provider = reducer.reduce(matrix)

    assert provider == "umap"
    assert coordinates.shape == (5, 3)
    assert coordinates[3, 2] == 1.0
    assert coordinates[4, 0] == 0.5


def test_configurable_provider_uses_minilm_when_available(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = ConfigurableEmbeddingProvider(
        {
            "embedding_provider": "minilm",
            "minilm_model_name": "fake-minilm",
        }
    )

    fake_module = ModuleType("sentence_transformers")

    class _FakeSentenceTransformer:
        def __init__(self, model_name: str, cache_folder: str | None = None) -> None:
            self.model_name = model_name
            self.cache_folder = cache_folder

        def encode(
            self,
            texts: list[str],
            *,
            convert_to_numpy: bool,
            show_progress_bar: bool,
            normalize_embeddings: bool,
        ) -> np.ndarray:
            assert self.model_name == "fake-minilm"
            assert self.cache_folder is None
            assert convert_to_numpy is True
            assert show_progress_bar is False
            assert normalize_embeddings is False
            return np.array([[float(len(texts[0])), 0.5, 1.0]])

    setattr(fake_module, "SentenceTransformer", _FakeSentenceTransformer)
    monkeypatch.setitem(sys.modules, "sentence_transformers", fake_module)

    result = provider.encode(["comentario"])

    assert result.provider == "sentence_transformers_minilm"
    assert result.matrix.shape == (1, 3)


def test_configurable_provider_falls_back_to_fasttext_when_minilm_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = ConfigurableEmbeddingProvider(
        {
            "embedding_provider": "auto",
            "preferred_embedding_provider": "minilm",
            "fallback_embedding_provider": "fasttext",
            "fasttext_model_path": "/tmp/model.bin",
        }
    )

    def fake_build_provider(name: str) -> object:
        if name == "minilm":
            class _FailingProvider:
                def encode(self, texts: list[str]) -> EmbeddingResult:
                    del texts
                    raise RuntimeError("MiniLM no disponible")

            return _FailingProvider()

        return _EmbedderStub(provider="facebook_fasttext")

    monkeypatch.setattr(provider, "_build_provider", fake_build_provider)

    result = provider.encode(["comentario de prueba"])

    assert result.provider == "facebook_fasttext"


def test_configurable_provider_raises_clear_error_when_all_providers_fail(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = ConfigurableEmbeddingProvider(
        {
            "embedding_provider": "auto",
            "preferred_embedding_provider": "minilm",
            "fallback_embedding_provider": "fasttext",
        }
    )

    class _AlwaysFailProvider:
        def __init__(self, label: str) -> None:
            self.label = label

        def encode(self, texts: list[str]) -> EmbeddingResult:
            del texts
            raise RuntimeError(f"{self.label} no disponible")

    monkeypatch.setattr(
        provider,
        "_build_provider",
        lambda name: _AlwaysFailProvider(name),
    )

    with pytest.raises(RuntimeError, match="No se pudieron generar embeddings") as exc_info:
        provider.encode(["comentario de prueba"])

    assert "minilm" in str(exc_info.value)
    assert "fasttext" in str(exc_info.value)


def test_minilm_provider_raises_clear_error_when_dependency_is_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = ConfigurableEmbeddingProvider(
        {
            "embedding_provider": "minilm",
            "minilm_model_name": "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        }
    )
    monkeypatch.delitem(sys.modules, "sentence_transformers", raising=False)
    original_import = __import__

    def fake_import(name: str, *args: Any, **kwargs: Any) -> ModuleType:
        if name == "sentence_transformers":
            raise ImportError("missing dependency")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr("builtins.__import__", fake_import)

    with pytest.raises(RuntimeError, match="sentence-transformers"):
        provider.encode(["comentario de prueba"])


def test_projection_build_for_exercise_reuses_remote_cache_without_recomputing() -> None:
    clean_comment = "hallazgo cuota ingreso estable"
    comment_hash = build_comment_hash(clean_comment, is_clean=True)
    remote_sync = _RemoteSyncStub(
        comment_events=[
            {
                "participant_id": "a1",
                "public_alias": "P-001",
                "exercise": "default_risk",
                "comment_text": "Hallazgo cuota ingreso estable",
                "comment_type": "analytics_comment",
                "clean_comment": clean_comment,
                "comment_hash": comment_hash,
                "updated_at": "2026-04-03T00:00:00Z",
                "source_sheet_row_number": 7,
            }
        ],
        embedding_rows=[
            {
                "participant_id": "a1",
                "exercise": "default_risk",
                "comment_hash": comment_hash,
                "embedding_provider": "sentence_transformers_minilm",
                "embedding_vector_json": "[0.1, 0.2, 0.3]",
            }
        ],
        projection_rows=[
            {
                "participant_id": "a1",
                "exercise": "default_risk",
                "comment_hash": comment_hash,
                "reduction_provider": "umap",
                "x": 4.0,
                "y": 5.0,
                "z": 6.0,
            }
        ],
    )

    service = CommentAnalyticsService(
        embedder=_SinglePointEmbedderStub(),
        reducer=_ReducerSingleStub(),
        remote_sync=remote_sync,
        comments_config={
            "embedding_version": "emb-v1",
            "projection_version": "proj-v1",
            "source_snapshot_limit": 20,
        },
    )

    projection = service.build_projection_for_exercise("default_risk", "a1")

    assert projection["points"][0]["x"] == 4.0
    assert projection["reduction_provider"] == "umap"
    assert remote_sync.saved_embeddings == []
    assert remote_sync.saved_projections == []


def test_projection_build_for_exercise_persists_missing_embedding_and_projection_cache() -> None:
    remote_sync = _RemoteSyncStub(
        comment_events=[
            {
                "participant_id": "a1",
                "public_alias": "P-001",
                "exercise": "default_risk",
                "comment_text": "Hallazgo cuota ingreso estable en mora",
                "comment_type": "analytics_comment",
                "updated_at": "2026-04-03T00:00:00Z",
                "source_sheet_row_number": 7,
            }
        ],
        embedding_rows=[],
        projection_rows=[],
    )

    service = CommentAnalyticsService(
        embedder=_SinglePointEmbedderStub(),
        reducer=_ReducerSingleStub(),
        remote_sync=remote_sync,
        comments_config={
            "embedding_version": "emb-v1",
            "projection_version": "proj-v1",
            "source_snapshot_limit": 20,
        },
    )

    projection = service.build_projection_for_exercise("default_risk", "a1")

    assert projection["points"][0]["x"] == 9.0
    assert projection["embedding_version"] == "emb-v1"
    assert projection["projection_version"] == "proj-v1"
    assert len(remote_sync.saved_embeddings) == 1
    assert remote_sync.saved_embeddings[0]["comment_hash"] == projection["points"][0]["comment_hash"]
    assert len(remote_sync.saved_projections) == 1
    assert remote_sync.saved_projections[0]["projection_version"] == "proj-v1"


def test_projection_reuses_same_cached_embedding_by_comment_hash_for_multiple_participants() -> None:
    shared_hash = build_comment_hash("ingreso estable deuda baja", is_clean=False)
    remote_sync = _RemoteSyncStub(
        comment_events=[
            {
                "participant_id": "a1",
                "public_alias": "P-001",
                "exercise": "default_risk",
                "comment_text": "Ingreso estable y deuda baja",
                "comment_type": "dataset_comment",
                "updated_at": "2026-04-03T00:00:00Z",
            },
            {
                "participant_id": "a2",
                "public_alias": "P-002",
                "exercise": "default_risk",
                "comment_text": "Ingreso estable y deuda baja",
                "comment_type": "analytics_comment",
                "updated_at": "2026-04-03T00:01:00Z",
            },
        ],
        embedding_rows=[
            {
                "participant_id": "a1",
                "exercise": "default_risk",
                "comment_hash": shared_hash,
                "embedding_provider": "sentence_transformers_minilm",
                "embedding_vector_json": "[0.1, 0.2, 0.3]",
            }
        ],
        projection_rows=[],
    )

    service = CommentAnalyticsService(
        embedder=_EmbedderStub(),
        reducer=_ReducerStub(),
        remote_sync=remote_sync,
        comments_config={
            "embedding_version": "emb-v1",
            "projection_version": "proj-v1",
            "source_snapshot_limit": 20,
        },
    )

    projection = service.build_projection_for_exercise("default_risk", "a1")

    assert len(projection["points"]) == 2
    assert remote_sync.saved_embeddings == []
    assert len(remote_sync.saved_projections) == 2
