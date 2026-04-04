from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Protocol

import numpy as np

from services.configuration import load_app_config


MINILM_PROVIDER_NAME = "sentence_transformers_minilm"
FASTTEXT_PROVIDER_NAME = "facebook_fasttext"


@dataclass(frozen=True)
class EmbeddingResult:
    matrix: np.ndarray
    provider: str


class EmbeddingProvider(Protocol):
    def encode(self, texts: list[str]) -> EmbeddingResult:
        ...


class MiniLMEmbeddingProvider:
    def __init__(
        self,
        *,
        model_name: str,
        cache_folder: str | None = None,
    ) -> None:
        self.model_name = model_name
        self.cache_folder = cache_folder

    def encode(self, texts: list[str]) -> EmbeddingResult:
        try:
            from sentence_transformers import SentenceTransformer  # type: ignore
        except Exception as exc:
            raise RuntimeError(
                "No se pudo importar sentence-transformers. Instala la dependencia del proyecto para usar MiniLM."
            ) from exc

        try:
            model = SentenceTransformer(self.model_name, cache_folder=self.cache_folder)
            matrix = np.asarray(
                model.encode(
                    texts,
                    convert_to_numpy=True,
                    show_progress_bar=False,
                    normalize_embeddings=False,
                ),
                dtype=float,
            )
        except Exception as exc:
            raise RuntimeError(
                "No se pudo cargar o ejecutar el modelo MiniLM configurado. Verifica el nombre del modelo y la instalación local."
            ) from exc

        return EmbeddingResult(matrix=matrix, provider=MINILM_PROVIDER_NAME)


class FastTextEmbeddingProvider:
    def __init__(self, *, model_path: str) -> None:
        self.model_path = model_path

    def encode(self, texts: list[str]) -> EmbeddingResult:
        if not self.model_path:
            raise RuntimeError(
                "Falta FASTTEXT_MODEL_PATH o fasttext_model_path. Configura un modelo fastText local para usar el fallback."
            )

        try:
            import fasttext  # type: ignore
        except Exception as exc:
            raise RuntimeError(
                "No se pudo importar fastText. Instala la dependencia del proyecto para usar el fallback local."
            ) from exc

        try:
            model = fasttext.load_model(self.model_path)
            matrix = np.vstack([model.get_sentence_vector(text) for text in texts])
        except Exception as exc:
            raise RuntimeError(
                "No se pudo cargar o ejecutar el modelo fastText configurado. Verifica la ruta del modelo local."
            ) from exc

        return EmbeddingResult(matrix=matrix, provider=FASTTEXT_PROVIDER_NAME)


class ConfigurableEmbeddingProvider:
    VALID_PROVIDER_MODES = {"minilm", "fasttext", "auto"}

    def __init__(self, comments_config: dict[str, Any] | None = None) -> None:
        config = comments_config or load_app_config().comments
        self.provider_mode = str(config.get("embedding_provider", "auto")).strip().lower() or "auto"
        self.preferred_provider = str(config.get("preferred_embedding_provider", "minilm")).strip().lower() or "minilm"
        self.fallback_provider = str(config.get("fallback_embedding_provider", "fasttext")).strip().lower() or "fasttext"
        self.minilm_model_name = os.getenv("MINILM_MODEL_NAME") or str(
            config.get("minilm_model_name", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
        )
        self.minilm_cache_folder = os.getenv("SENTENCE_TRANSFORMERS_HOME") or config.get(
            "minilm_cache_folder"
        )
        self.fasttext_model_path = os.getenv("FASTTEXT_MODEL_PATH") or str(config.get("fasttext_model_path", ""))

        if self.provider_mode not in self.VALID_PROVIDER_MODES:
            raise RuntimeError(
                "embedding_provider debe ser 'minilm', 'fasttext' o 'auto'."
            )

    def encode(self, texts: list[str]) -> EmbeddingResult:
        errors: list[str] = []
        for provider_key in self._resolve_provider_chain():
            try:
                return self._build_provider(provider_key).encode(texts)
            except RuntimeError as exc:
                errors.append(f"{provider_key}: {exc}")
                if self.provider_mode != "auto":
                    raise RuntimeError(str(exc)) from exc

        detail = "; ".join(errors) if errors else "sin detalles disponibles"
        raise RuntimeError(
            "No se pudieron generar embeddings con los proveedores configurados. "
            f"Intentos realizados: {detail}"
        )

    def _resolve_provider_chain(self) -> list[str]:
        if self.provider_mode != "auto":
            return [self.provider_mode]

        chain: list[str] = []
        for provider_name in [self.preferred_provider, self.fallback_provider]:
            if provider_name in {"minilm", "fasttext"} and provider_name not in chain:
                chain.append(provider_name)
        return chain or ["minilm", "fasttext"]

    def _build_provider(self, provider_name: str) -> EmbeddingProvider:
        if provider_name == "minilm":
            return MiniLMEmbeddingProvider(
                model_name=self.minilm_model_name,
                cache_folder=str(self.minilm_cache_folder) if self.minilm_cache_folder else None,
            )
        if provider_name == "fasttext":
            return FastTextEmbeddingProvider(model_path=self.fasttext_model_path)
        raise RuntimeError("Proveedor de embeddings no soportado. Usa 'minilm' o 'fasttext'.")
