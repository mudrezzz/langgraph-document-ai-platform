from __future__ import annotations

from functools import lru_cache

from application.document_service import DocumentApplicationService
from application.retrieval_service import RetrievalApplicationService
from application.task_service import TaskApplicationService
from infra.postgres.checkpoint_store import LangGraphPostgresCheckpointStore
from infra.postgres.config import PostgresSettings
from infra.postgres.document_repository import PostgresDocumentRepository
from infra.postgres.task_registry import PostgresTaskRegistry


class ApiContainer:
    """DI-контейнер API сервиса."""

    def __init__(self) -> None:
        settings = PostgresSettings.from_env()
        use_fallback = settings.allow_fallback_persistence
        checkpoint_store = LangGraphPostgresCheckpointStore.from_settings(
            settings,
            use_fallback_if_unset=use_fallback,
        )
        registry = PostgresTaskRegistry.from_settings(
            settings,
            use_fallback_if_unset=use_fallback,
        )
        document_repository = PostgresDocumentRepository.from_settings(
            settings,
            use_fallback_if_unset=use_fallback,
        )
        task_service = TaskApplicationService(registry=registry, checkpoint_store=checkpoint_store)

        self.settings = settings
        self.task_service = task_service
        self.document_service = DocumentApplicationService(repository=document_repository)
        self.retrieval_service = RetrievalApplicationService(task_service=task_service)


@lru_cache(maxsize=1)
def get_container() -> ApiContainer:
    """Возвращает singleton-контейнер API зависимостей."""

    return ApiContainer()
