from __future__ import annotations

from functools import lru_cache

from services.configuration import AppConfig, load_app_config
from services.modeling import (
    DatasetCatalog,
    ModelEvaluationService,
    ModelRegistry,
    PredictionService,
)
from services.remote_sync import build_remote_sync_client
from services.session_service import SessionService
from services.storage import JsonStateStore
from services.storage_sqlite import SQLiteStateStore
from services.submission_validation import SubmissionValidationService
from services.text_pipeline import CommentAnalyticsService, CommentKeywordService


class AppContainer:
    def __init__(self, config: AppConfig | None = None) -> None:
        self.config = config or load_app_config()
        self.store = self._build_store()
        self.remote_sync = build_remote_sync_client(self.config)
        self.sessions = SessionService(self.store, self.remote_sync)
        self.catalog = DatasetCatalog()
        self.models = ModelRegistry(self.catalog)
        self.predictions = PredictionService(self.models)
        self.model_evaluation = ModelEvaluationService(self.catalog)
        self.comments = CommentAnalyticsService(
            store=self.store, remote_sync=self.remote_sync
        )
        self.keywords = CommentKeywordService()
        self.submission_validation = SubmissionValidationService()

    def _build_store(self) -> JsonStateStore | SQLiteStateStore:
        if self.config.persistence_store == "sqlite":
            return SQLiteStateStore(db_path=self.config.sqlite_path)
        if self.config.persistence_store == "json":
            return JsonStateStore(path=self.config.json_state_path)
        raise ValueError(
            f"Unsupported persistence store: {self.config.persistence_store}"
        )


@lru_cache(maxsize=1)
def get_container() -> AppContainer:
    return AppContainer()
