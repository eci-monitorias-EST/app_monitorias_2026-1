from __future__ import annotations

import sys
from types import ModuleType
from typing import Any

import numpy as np
import pytest

from domain.models import CompletedComment
from services.embedding_providers import ConfigurableEmbeddingProvider, EmbeddingResult
from services.text_pipeline import CommentAnalyticsService, TextCleaner


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


def test_cleaner_removes_noise() -> None:
    cleaner = TextCleaner()
    cleaned = cleaner.clean("¡Visité https://bankify.test y EL modelo fue MUY claro!")
    assert "https" not in cleaned
    assert "muy" not in cleaned
    assert "modelo" in cleaned


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
