from __future__ import annotations

import logging
import re
import unicodedata

import numpy as np
from sklearn.decomposition import PCA
from sklearn.feature_extraction.text import TfidfVectorizer

from domain.models import CompletedComment
from services.configuration import load_app_config
from services.embedding_providers import ConfigurableEmbeddingProvider, EmbeddingProvider


LOGGER = logging.getLogger(__name__)


SPANISH_STOPWORDS = {
    "de", "la", "el", "los", "las", "que", "y", "o", "en", "un", "una", "para", "por",
    "con", "del", "al", "se", "su", "sus", "me", "mi", "mis", "es", "son", "muy", "mas",
    "pero", "porque", "como", "lo", "le", "les", "ha", "han", "fue", "ser", "estar",
}

class TextCleaner:
    def clean(self, text: str) -> str:
        normalized = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
        normalized = normalized.lower()
        normalized = re.sub(r"https?://\S+|www\.\S+", " ", normalized)
        normalized = re.sub(r"[^a-z0-9\s]", " ", normalized)
        normalized = re.sub(r"\s+", " ", normalized).strip()
        tokens = [token for token in normalized.split() if token not in SPANISH_STOPWORDS]
        return " ".join(tokens)

class DimensionalityReducer:
    def reduce(self, matrix: np.ndarray) -> tuple[np.ndarray, str]:
        if matrix.shape[0] == 1:
            return np.array([[0.0, 0.0, 0.0]]), "single_point"

        if matrix.shape[0] <= 4:
            return self._reduce_small_sample(matrix)

        try:
            import umap  # type: ignore

            reducer = umap.UMAP(
                n_components=3,
                n_neighbors=min(10, max(2, matrix.shape[0] - 1)),
                random_state=42,
            )
            return reducer.fit_transform(matrix), "umap"
        except Exception:
            LOGGER.warning(
                "UMAP falló para %s comentarios; usando fallback determinístico.",
                matrix.shape[0],
                exc_info=True,
            )
            return self._reduce_small_sample(matrix)

    def _reduce_small_sample(self, matrix: np.ndarray) -> tuple[np.ndarray, str]:
        sample_count = matrix.shape[0]
        feature_count = matrix.shape[1] if matrix.ndim > 1 else 1
        component_count = min(3, sample_count, feature_count)

        if component_count <= 0:
            return np.zeros((sample_count, 3), dtype=float), "small_sample_fallback"

        reducer = PCA(n_components=component_count, svd_solver="full")
        reduced = reducer.fit_transform(matrix)
        coordinates = np.zeros((sample_count, 3), dtype=float)
        coordinates[:, :component_count] = reduced

        LOGGER.info(
            "Usando fallback determinístico para proyección 3D con %s comentarios.",
            sample_count,
        )
        return coordinates, "small_sample_fallback"


class CommentAnalyticsService:
    def __init__(
        self,
        *,
        embedder: EmbeddingProvider | None = None,
        reducer: DimensionalityReducer | None = None,
    ) -> None:
        self.cleaner = TextCleaner()
        self.embedder = embedder or ConfigurableEmbeddingProvider(load_app_config().comments)
        self.reducer = reducer or DimensionalityReducer()

    def build_projection(self, comments: list[CompletedComment]) -> dict[str, object]:
        if not comments:
            return {"points": [], "embedding_provider": "none", "reduction_provider": "none"}

        cleaned = [self.cleaner.clean(comment.combined_comment) for comment in comments]
        embedding = self.embedder.encode(cleaned)
        coordinates, reduction_provider = self.reducer.reduce(embedding.matrix)
        points = []
        for index, comment in enumerate(comments):
            points.append(
                {
                    "participant_id": comment.participant_id,
                    "public_alias": comment.public_alias,
                    "comment": comment.combined_comment,
                    "clean_comment": cleaned[index],
                    "x": float(coordinates[index, 0]),
                    "y": float(coordinates[index, 1]),
                    "z": float(coordinates[index, 2]),
                    "current_user": comment.current_user,
                }
            )
        return {
            "points": points,
            "embedding_provider": embedding.provider,
            "reduction_provider": reduction_provider,
        }


class CommentKeywordService:
    def summarize_keywords(self, texts: list[str], limit: int = 12) -> list[dict[str, object]]:
        if not texts:
            return []
        vectorizer = TfidfVectorizer(max_features=limit, ngram_range=(1, 2))
        matrix = vectorizer.fit_transform(texts)
        scores = np.asarray(matrix.mean(axis=0)).ravel()
        items = [
            {"keyword": keyword, "score": float(scores[index])}
            for keyword, index in vectorizer.vocabulary_.items()
        ]
        return sorted(items, key=lambda item: item["score"], reverse=True)
