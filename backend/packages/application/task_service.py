from __future__ import annotations

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


class InMemoryTaskRegistry:
    """Простая in-memory регистрация задач для API слоя."""

    def __init__(self) -> None:
        self._tasks: dict[str, TaskRecord] = {}

    def save(self, record: TaskRecord) -> None:
        self._tasks[record.task_id] = record

    def get(self, task_id: str) -> TaskRecord:
        item = self._tasks.get(task_id)
        if item is None:
            raise TaskNotFoundError(f"Задача {task_id} не найдена")
        return item


class TaskApplicationService:
    """Сервис управления состоянием задач и checkpoint payload."""

    def __init__(self, registry: InMemoryTaskRegistry, checkpoint_store: ICheckpointStore) -> None:
        self._registry = registry
        self._checkpoint_store = checkpoint_store

    def create_task(self, task_type: str) -> TaskRecord:
        task = TaskRecord(
            task_id=str(uuid4()),
            task_type=task_type,
            status="running",
            current_node="start",
            details={},
        )
        self._registry.save(task)
        return task

    def complete_task(self, task_id: str, state_payload: dict, details: dict | None = None) -> TaskRecord:
        task = self._registry.get(task_id)
        task = task.model_copy(
            update={
                "status": "completed",
                "current_node": "completed",
                "details": details or task.details,
            }
        )
        self._checkpoint_store.save_checkpoint(task_id, state_payload)
        self._registry.save(task)
        return task

    def update_task(self, task_id: str, **kwargs) -> TaskRecord:
        task = self._registry.get(task_id)
        updated = task.model_copy(update=kwargs)
        self._registry.save(updated)
        return updated

    def get_task(self, task_id: str) -> TaskRecord:
        return self._registry.get(task_id)

    def get_state_payload(self, task_id: str) -> dict:
        payload = self._checkpoint_store.load_checkpoint(task_id)
        if payload is None:
            raise TaskNotFoundError(f"Checkpoint для задачи {task_id} не найден")
        return payload