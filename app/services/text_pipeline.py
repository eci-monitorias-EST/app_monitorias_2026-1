from __future__ import annotations

import hashlib
import json
import logging
import re
import unicodedata
from typing import Any

import numpy as np
from sklearn.decomposition import PCA
from sklearn.feature_extraction.text import TfidfVectorizer

from domain.models import CompletedComment
from services.configuration import load_app_config
from services.embedding_providers import ConfigurableEmbeddingProvider, EmbeddingProvider
from services.remote_sync import RemoteSyncClient
from services.storage import JsonStateStore
from services.submission_validation import SubmissionValidationService


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


def combine_comment_fragments(*fragments: str) -> str:
    return " ".join(str(fragment).strip() for fragment in fragments if str(fragment).strip()).strip()


def build_comment_hash(comment: str, *, cleaner: TextCleaner | None = None, is_clean: bool = False) -> str:
    normalized = comment.strip() if is_clean else (cleaner or TextCleaner()).clean(comment)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

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
        store: JsonStateStore | None = None,
        remote_sync: RemoteSyncClient | None = None,
        comments_config: dict[str, Any] | None = None,
    ) -> None:
        self.config = comments_config or load_app_config().comments
        self.cleaner = TextCleaner()
        self.embedder = embedder or ConfigurableEmbeddingProvider(self.config)
        self.reducer = reducer or DimensionalityReducer()
        self.store = store
        self.remote_sync = remote_sync
        self.validator = SubmissionValidationService()
        self.embedding_version = str(self.config.get("embedding_version", "minilm_clean_comment_v1")).strip()
        self.projection_version = str(self.config.get("projection_version", "projection_cache_v1")).strip()
        self.source_snapshot_limit = int(self.config.get("source_snapshot_limit", 500))

    def build_projection_for_exercise(
        self,
        exercise: str,
        current_participant_id: str,
    ) -> dict[str, object]:
        return self.build_projection(self.list_comments(exercise, current_participant_id))

    def list_comments(self, exercise: str, current_participant_id: str) -> list[CompletedComment]:
        if self.remote_sync is not None:
            remote_rows = self.remote_sync.query_projection_comments(exercise, self.source_snapshot_limit)
            if remote_rows is not None:
                return self._build_comments_from_remote_rows(remote_rows, current_participant_id)

        if self.store is None:
            return []
        return self.store.list_completed_comments(exercise, current_participant_id)

    def build_projection(self, comments: list[CompletedComment]) -> dict[str, object]:
        if not comments:
            return {
                "points": [],
                "embedding_provider": "none",
                "reduction_provider": "none",
                "embedding_version": self.embedding_version,
                "projection_version": self.projection_version,
            }

        normalized_comments = [self._normalize_comment(comment) for comment in comments]
        embedding_matrix, embedding_provider = self._resolve_embeddings(normalized_comments)
        coordinates, reduction_provider = self._resolve_projection(
            normalized_comments,
            embedding_matrix,
            embedding_provider,
        )
        points = []
        for index, comment in enumerate(normalized_comments):
            points.append(
                {
                    "participant_id": comment.participant_id,
                    "public_alias": comment.public_alias,
                    "comment": comment.combined_comment,
                    "clean_comment": comment.clean_comment,
                    "comment_hash": comment.comment_hash,
                    "x": float(coordinates[index, 0]),
                    "y": float(coordinates[index, 1]),
                    "z": float(coordinates[index, 2]),
                    "current_user": comment.current_user,
                }
            )
        return {
            "points": points,
            "embedding_provider": embedding_provider,
            "reduction_provider": reduction_provider,
            "embedding_version": self.embedding_version,
            "projection_version": self.projection_version,
        }

    def _build_comments_from_remote_rows(
        self,
        rows: list[dict[str, Any]],
        current_participant_id: str,
    ) -> list[CompletedComment]:
        comments: list[CompletedComment] = []
        for row in rows:
            combined_comment = str(row.get("combined_comment", "")).strip() or combine_comment_fragments(
                str(row.get("dataset_comment", "")),
                str(row.get("analytics_comment", "")),
                str(row.get("prediction_reflection", "")),
            )
            if not combined_comment:
                continue
            if not self.validator.has_meaningful_learning_text(combined_comment):
                continue
            comments.append(
                CompletedComment(
                    participant_id=str(row.get("participant_id", "")).strip(),
                    public_alias=str(row.get("public_alias", "")).strip(),
                    exercise=str(row.get("exercise", "")).strip(),
                    combined_comment=combined_comment,
                    current_user=str(row.get("participant_id", "")).strip() == current_participant_id,
                    source_updated_at=str(row.get("updated_at", "")).strip(),
                    source_sheet_row_number=int(row.get("source_sheet_row_number", 0) or 0),
                )
            )
        return comments

    def _normalize_comment(self, comment: CompletedComment) -> CompletedComment:
        clean_comment = comment.clean_comment or self.cleaner.clean(comment.combined_comment)
        return CompletedComment(
            participant_id=comment.participant_id,
            public_alias=comment.public_alias,
            exercise=comment.exercise,
            combined_comment=comment.combined_comment,
            current_user=comment.current_user,
            clean_comment=clean_comment,
            comment_hash=comment.comment_hash or build_comment_hash(clean_comment, is_clean=True),
            source_updated_at=comment.source_updated_at,
            source_sheet_row_number=comment.source_sheet_row_number,
        )

    def _resolve_embeddings(
        self,
        comments: list[CompletedComment],
    ) -> tuple[np.ndarray, str]:
        cached_rows_by_key = self._query_embedding_cache_rows(comments)
        vectors_by_key: dict[tuple[str, str, str], np.ndarray] = {}
        embedding_provider = ""
        missing_comments: list[CompletedComment] = []

        for comment in comments:
            key = (comment.participant_id, comment.exercise, comment.comment_hash)
            cached_row = cached_rows_by_key.get(key)
            if cached_row is None:
                missing_comments.append(comment)
                continue
            vectors_by_key[key] = self._parse_embedding_vector(cached_row)
            embedding_provider = embedding_provider or str(cached_row.get("embedding_provider", "")).strip()

        if missing_comments:
            result = self.embedder.encode([comment.clean_comment for comment in missing_comments])
            embedding_provider = embedding_provider or result.provider
            upsert_rows: list[dict[str, Any]] = []
            for index, comment in enumerate(missing_comments):
                key = (comment.participant_id, comment.exercise, comment.comment_hash)
                vector = np.asarray(result.matrix[index], dtype=float)
                vectors_by_key[key] = vector
                upsert_rows.append(
                    {
                        "participant_id": comment.participant_id,
                        "exercise": comment.exercise,
                        "comment_hash": comment.comment_hash,
                        "embedding_version": self.embedding_version,
                        "embedding_provider": result.provider,
                        "comment_text": comment.combined_comment,
                        "clean_comment": comment.clean_comment,
                        "embedding_vector": vector.tolist(),
                        "source_updated_at": comment.source_updated_at,
                        "source_sheet_row_number": comment.source_sheet_row_number,
                    }
                )
            if self.remote_sync is not None and upsert_rows:
                self.remote_sync.upsert_embeddings_cache(upsert_rows)

        matrix = np.vstack(
            [vectors_by_key[(comment.participant_id, comment.exercise, comment.comment_hash)] for comment in comments]
        )
        return matrix, embedding_provider or "unknown"

    def _resolve_projection(
        self,
        comments: list[CompletedComment],
        embedding_matrix: np.ndarray,
        embedding_provider: str,
    ) -> tuple[np.ndarray, str]:
        cached_rows_by_key = self._query_projection_cache_rows(comments)
        cached_coordinates: list[np.ndarray] = []
        cached_reduction_provider = ""
        all_cached = True

        for comment in comments:
            key = (comment.participant_id, comment.exercise, comment.comment_hash)
            cached_row = cached_rows_by_key.get(key)
            if cached_row is None:
                all_cached = False
                break
            cached_coordinates.append(
                np.array(
                    [
                        float(cached_row.get("x", 0.0)),
                        float(cached_row.get("y", 0.0)),
                        float(cached_row.get("z", 0.0)),
                    ],
                    dtype=float,
                )
            )
            cached_reduction_provider = cached_reduction_provider or str(
                cached_row.get("reduction_provider", "")
            ).strip()

        if all_cached:
            return np.vstack(cached_coordinates), cached_reduction_provider or "cache"

        coordinates, reduction_provider = self.reducer.reduce(embedding_matrix)
        if self.remote_sync is not None:
            self.remote_sync.upsert_projection_cache(
                [
                    {
                        "participant_id": comment.participant_id,
                        "exercise": comment.exercise,
                        "comment_hash": comment.comment_hash,
                        "projection_version": self.projection_version,
                        "embedding_provider": embedding_provider,
                        "reduction_provider": reduction_provider,
                        "public_alias": comment.public_alias,
                        "comment_text": comment.combined_comment,
                        "clean_comment": comment.clean_comment,
                        "x": float(coordinates[index, 0]),
                        "y": float(coordinates[index, 1]),
                        "z": float(coordinates[index, 2]),
                        "source_updated_at": comment.source_updated_at,
                        "source_sheet_row_number": comment.source_sheet_row_number,
                    }
                    for index, comment in enumerate(comments)
                ]
            )
        return coordinates, reduction_provider

    def _query_embedding_cache_rows(
        self,
        comments: list[CompletedComment],
    ) -> dict[tuple[str, str, str], dict[str, Any]]:
        if self.remote_sync is None:
            return {}
        rows = self.remote_sync.query_embeddings_cache(
            exercise=comments[0].exercise,
            embedding_version=self.embedding_version,
            participant_ids=[comment.participant_id for comment in comments],
            comment_hashes=[comment.comment_hash for comment in comments],
        )
        if rows is None:
            return {}
        return {
            (
                str(row.get("participant_id", "")).strip(),
                str(row.get("exercise", "")).strip(),
                str(row.get("comment_hash", "")).strip(),
            ): row
            for row in rows
        }

    def _query_projection_cache_rows(
        self,
        comments: list[CompletedComment],
    ) -> dict[tuple[str, str, str], dict[str, Any]]:
        if self.remote_sync is None:
            return {}
        rows = self.remote_sync.query_projection_cache(
            exercise=comments[0].exercise,
            projection_version=self.projection_version,
            participant_ids=[comment.participant_id for comment in comments],
            comment_hashes=[comment.comment_hash for comment in comments],
        )
        if rows is None:
            return {}
        return {
            (
                str(row.get("participant_id", "")).strip(),
                str(row.get("exercise", "")).strip(),
                str(row.get("comment_hash", "")).strip(),
            ): row
            for row in rows
        }

    @staticmethod
    def _parse_embedding_vector(row: dict[str, Any]) -> np.ndarray:
        raw_value = row.get("embedding_vector_json", row.get("embedding_vector", []))
        if isinstance(raw_value, str):
            parsed = json.loads(raw_value or "[]")
        else:
            parsed = raw_value
        return np.asarray(parsed, dtype=float)


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
