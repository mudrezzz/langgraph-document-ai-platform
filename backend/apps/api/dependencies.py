from __future__ import annotations

from functools import lru_cache

from application.retrieval_service import RetrievalApplicationService
from application.task_service import InMemoryTaskRegistry, TaskApplicationService
from infra.postgres.checkpoint_store import LangGraphPostgresCheckpointStore


class ApiContainer:
    """DI-контейнер API сервиса."""

    def __init__(self) -> None:
        checkpoint_store = LangGraphPostgresCheckpointStore()
        registry = InMemoryTaskRegistry()
        task_service = TaskApplicationService(registry=registry, checkpoint_store=checkpoint_store)

        self.task_service = task_service
        self.retrieval_service = RetrievalApplicationService(task_service=task_service)


@lru_cache(maxsize=1)
def get_container() -> ApiContainer:
    """Возвращает singleton-контейнер API зависимостей."""

    return ApiContainer()