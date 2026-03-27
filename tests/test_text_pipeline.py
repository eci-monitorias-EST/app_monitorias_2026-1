from __future__ import annotations

import numpy as np

from domain.models import CompletedComment
from services.text_pipeline import CommentAnalyticsService, EmbeddingResult, TextCleaner


def test_cleaner_removes_noise() -> None:
    cleaner = TextCleaner()
    cleaned = cleaner.clean("¡Visité https://bankify.test y EL modelo fue MUY claro!")
    assert "https" not in cleaned
    assert "muy" not in cleaned
    assert "modelo" in cleaned


def test_projection_builds_3d_points() -> None:
    service = CommentAnalyticsService()
    service.embedder = type(
        "EmbedderStub",
        (),
        {
            "encode": lambda self, texts: EmbeddingResult(
                matrix=np.array([[0.1, 0.2, 0.3], [0.3, 0.2, 0.1]]),
                provider="facebook_fasttext",
            )
        },
    )()
    service.reducer = type(
        "ReducerStub",
        (),
        {
            "reduce": lambda self, matrix: (
                np.array([[1.0, 2.0, 3.0], [3.0, 2.0, 1.0]]),
                "umap",
            )
        },
    )()
    projection = service.build_projection(
        [
            CompletedComment("a1", "P-001", "default_risk", "El dashboard mostró mora alta", True),
            CompletedComment("a2", "P-002", "default_risk", "La edad y el atraso explican el riesgo", False),
        ]
    )
    assert len(projection["points"]) == 2
    assert projection["points"][0]["x"] == 1.0
    assert projection["embedding_provider"] == "facebook_fasttext"
