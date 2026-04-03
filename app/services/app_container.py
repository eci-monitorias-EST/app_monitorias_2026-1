from __future__ import annotations

from functools import lru_cache

from services.modeling import DatasetCatalog, ModelRegistry, PredictionService
from services.remote_sync import build_remote_sync_client
from services.session_service import SessionService
from services.storage import JsonStateStore
from services.submission_validation import SubmissionValidationService
from services.text_pipeline import CommentAnalyticsService, CommentKeywordService


class AppContainer:
    def __init__(self) -> None:
        self.store = JsonStateStore()
        self.remote_sync = build_remote_sync_client()
        self.sessions = SessionService(self.store, self.remote_sync)
        self.catalog = DatasetCatalog()
        self.models = ModelRegistry(self.catalog)
        self.predictions = PredictionService(self.models)
        self.comments = CommentAnalyticsService()
        self.keywords = CommentKeywordService()
        self.submission_validation = SubmissionValidationService()


@lru_cache(maxsize=1)
def get_container() -> AppContainer:
    return AppContainer()
