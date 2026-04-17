from __future__ import annotations

from functools import lru_cache

from application.retrieval_service import RetrievalApplicationService
from application.task_service import InMemoryTaskRegistry, TaskApplicationService
from infra.postgres.checkpoint_store import LangGraphPostgresCheckpointStore
from infra.postgres.config import PostgresSettings


class ApiContainer:
    """DI-контейнер API сервиса."""

    def __init__(self) -> None:
        settings = PostgresSettings.from_env()
        checkpoint_store = LangGraphPostgresCheckpointStore.from_settings(settings, use_fallback_if_unset=True)
        registry = InMemoryTaskRegistry()
        task_service = TaskApplicationService(registry=registry, checkpoint_store=checkpoint_store)

        self.settings = settings
        self.task_service = task_service
        self.retrieval_service = RetrievalApplicationService(task_service=task_service)


@lru_cache(maxsize=1)
def get_container() -> ApiContainer:
    """Возвращает singleton-контейнер API зависимостей."""

    return ApiContainer()