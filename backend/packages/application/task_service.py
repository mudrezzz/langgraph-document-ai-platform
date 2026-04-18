from __future__ import annotations

from datetime import datetime, timezone
from typing import Protocol, runtime_checkable
from uuid import uuid4

from pydantic import BaseModel, Field

from application.errors import TaskNotFoundError
from framework.stores.interfaces import ICheckpointStore


class TaskRecord(BaseModel):
    """Внутренняя запись о lifecycle задачи."""

    task_id: str
    task_type: str
    status: str
    current_node: str | None = None
    details: dict = Field(default_factory=dict)
    created_at: datetime | None = None
    updated_at: datetime | None = None


@runtime_checkable
class TaskRegistry(Protocol):
    """Контракт хранилища lifecycle-записей задач."""

    def save(self, record: TaskRecord) -> None:
        """Сохраняет или обновляет запись задачи."""

    def get(self, task_id: str) -> TaskRecord:
        """Возвращает запись задачи по идентификатору."""

    def list_tasks(self, limit: int = 50, offset: int = 0) -> list[TaskRecord]:
        """Возвращает историю задач в порядке убывания updated_at."""


class InMemoryTaskRegistry(TaskRegistry):
    """Простая in-memory регистрация задач для API слоя."""

    def __init__(self) -> None:
        self._tasks: dict[str, TaskRecord] = {}

    def save(self, record: TaskRecord) -> None:
        now_utc = datetime.now(timezone.utc)
        current = self._tasks.get(record.task_id)

        # При первом сохранении фиксируем created_at, при последующих обновляем updated_at.
        if current is None:
            created_at = record.created_at or now_utc
            updated_at = record.updated_at or now_utc
        else:
            created_at = current.created_at or record.created_at or now_utc
            updated_at = now_utc

        self._tasks[record.task_id] = record.model_copy(update={"created_at": created_at, "updated_at": updated_at})

    def get(self, task_id: str) -> TaskRecord:
        item = self._tasks.get(task_id)
        if item is None:
            raise TaskNotFoundError(f"Задача {task_id} не найдена")
        return item

    def list_tasks(self, limit: int = 50, offset: int = 0) -> list[TaskRecord]:
        ordered = sorted(
            self._tasks.values(),
            key=lambda item: item.updated_at or item.created_at or datetime.min.replace(tzinfo=timezone.utc),
            reverse=True,
        )
        return ordered[offset : offset + limit]


class TaskApplicationService:
    """Сервис управления состоянием задач и checkpoint payload."""

    def __init__(self, registry: TaskRegistry, checkpoint_store: ICheckpointStore) -> None:
        self._registry = registry
        self._checkpoint_store = checkpoint_store

    def create_task(self, task_type: str) -> TaskRecord:
        now_utc = datetime.now(timezone.utc)
        task = TaskRecord(
            task_id=str(uuid4()),
            task_type=task_type,
            status="running",
            current_node="start",
            details={},
            created_at=now_utc,
            updated_at=now_utc,
        )
        self._registry.save(task)
        return task

    def save_checkpoint(self, task_id: str, state_payload: dict) -> None:
        """Сохраняет checkpoint без изменения статуса задачи."""

        self._checkpoint_store.save_checkpoint(task_id, state_payload)

    def complete_task(self, task_id: str, state_payload: dict, details: dict | None = None) -> TaskRecord:
        """Помечает задачу завершенной и фиксирует checkpoint."""

        self.save_checkpoint(task_id, state_payload)
        return self.update_task(
            task_id,
            status="completed",
            current_node="completed",
            details=details or self._registry.get(task_id).details,
        )

    def fail_task(self, task_id: str, state_payload: dict, error_message: str) -> TaskRecord:
        """Помечает задачу ошибочной и сохраняет последнее валидное состояние."""

        self.save_checkpoint(task_id, state_payload)
        return self.update_task(
            task_id,
            status="failed",
            current_node="failed",
            details={"error": error_message},
        )

    def update_task(self, task_id: str, **kwargs) -> TaskRecord:
        task = self._registry.get(task_id)
        updated = task.model_copy(
            update={
                **kwargs,
                "created_at": task.created_at,
                "updated_at": datetime.now(timezone.utc),
            }
        )
        self._registry.save(updated)
        return updated

    def get_task(self, task_id: str) -> TaskRecord:
        return self._registry.get(task_id)

    def list_tasks(self, limit: int = 50, offset: int = 0) -> list[TaskRecord]:
        return self._registry.list_tasks(limit=limit, offset=offset)

    def get_state_payload(self, task_id: str) -> dict:
        payload = self._checkpoint_store.load_checkpoint(task_id)
        if payload is None:
            raise TaskNotFoundError(f"Checkpoint для задачи {task_id} не найден")
        return payload
