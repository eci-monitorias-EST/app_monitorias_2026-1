from __future__ import annotations

import os
import re
import unicodedata
from dataclasses import dataclass

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

from domain.models import CompletedComment
from services.configuration import load_app_config


SPANISH_STOPWORDS = {
    "de", "la", "el", "los", "las", "que", "y", "o", "en", "un", "una", "para", "por",
    "con", "del", "al", "se", "su", "sus", "me", "mi", "mis", "es", "son", "muy", "mas",
    "pero", "porque", "como", "lo", "le", "les", "ha", "han", "fue", "ser", "estar",
}


@dataclass
class EmbeddingResult:
    matrix: np.ndarray
    provider: str


class TextCleaner:
    def clean(self, text: str) -> str:
        normalized = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
        normalized = normalized.lower()
        normalized = re.sub(r"https?://\S+|www\.\S+", " ", normalized)
        normalized = re.sub(r"[^a-z0-9\s]", " ", normalized)
        normalized = re.sub(r"\s+", " ", normalized).strip()
        tokens = [token for token in normalized.split() if token not in SPANISH_STOPWORDS]
        return " ".join(tokens)


class FacebookEmbeddingProvider:
    def __init__(self) -> None:
        config = load_app_config()
        comments = config.comments
        self.embedding_dimensions = int(comments.get("embedding_dimensions", 64))
        self.model_path = os.getenv("FASTTEXT_MODEL_PATH") or comments.get("fasttext_model_path", "")

    def encode(self, texts: list[str]) -> EmbeddingResult:
        if not self.model_path:
            raise RuntimeError(
                "Falta FASTTEXT_MODEL_PATH. Configura un modelo fastText de Facebook para generar embeddings reales."
            )
        try:
            import fasttext  # type: ignore
        except Exception as exc:
            raise RuntimeError(
                "No se pudo importar fastText. Instala la dependencia del proyecto para usar embeddings de Facebook."
            ) from exc

        model = fasttext.load_model(self.model_path)
        vectors = np.vstack([model.get_sentence_vector(text) for text in texts])
        return EmbeddingResult(matrix=vectors, provider="facebook_fasttext")


class DimensionalityReducer:
    def reduce(self, matrix: np.ndarray) -> tuple[np.ndarray, str]:
        if matrix.shape[0] == 1:
            return np.array([[0.0, 0.0, 0.0]]), "single_point"
        try:
            import umap  # type: ignore

            reducer = umap.UMAP(
                n_components=3,
                n_neighbors=min(10, max(2, matrix.shape[0] - 1)),
                random_state=42,
            )
            return reducer.fit_transform(matrix), "umap"
        except Exception as exc:
            raise RuntimeError("No se pudo ejecutar UMAP para la proyección 3D de comentarios.") from exc


class CommentAnalyticsService:
    def __init__(self) -> None:
        self.cleaner = TextCleaner()
        self.embedder = FacebookEmbeddingProvider()
        self.reducer = DimensionalityReducer()

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
