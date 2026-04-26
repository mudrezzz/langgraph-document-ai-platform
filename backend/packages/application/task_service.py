from __future__ import annotations

import base64
import json
import os
from datetime import datetime, timezone
from typing import Any, Protocol, runtime_checkable
from uuid import uuid4

from pydantic import BaseModel, Field

from application.errors import InvalidCursorError, TaskNotFoundError
from framework.stores.interfaces import ICheckpointStore
from framework.workflows.base import WorkflowNodeEventRecord, WorkflowNodeEventSink


class TaskRecord(BaseModel):
    """Внутренняя запись о lifecycle задачи."""

    task_id: str
    task_type: str
    status: str
    current_node: str | None = None
    details: dict = Field(default_factory=dict)
    created_at: datetime | None = None
    updated_at: datetime | None = None


class TaskEventRecord(BaseModel):
    """Аудит-событие перехода статуса задачи."""

    event_id: int | None = None
    task_id: str
    task_type: str
    from_status: str | None = None
    to_status: str
    from_current_node: str | None = None
    to_current_node: str | None = None
    event_payload: dict = Field(default_factory=dict)
    created_at: datetime | None = None


class TaskListPage(BaseModel):
    """Страница истории задач с курсорной пагинацией."""

    items: list[TaskRecord] = Field(default_factory=list)
    limit: int
    total_returned: int
    next_cursor: str | None = None
    has_more: bool = False


class TaskEventListPage(BaseModel):
    """Страница аудита переходов статусов с курсорной пагинацией."""

    items: list[TaskEventRecord] = Field(default_factory=list)
    limit: int
    total_returned: int
    next_cursor: str | None = None
    has_more: bool = False


class TaskEventTransitionStat(BaseModel):
    """Агрегированная статистика по переходу статусов."""

    from_status: str | None = None
    to_status: str
    total: int


class TaskEventSummary(BaseModel):
    """Сводка аудита переходов статусов."""

    total_events: int
    unique_tasks: int
    transitions: list[TaskEventTransitionStat] = Field(default_factory=list)


class TaskStatusStat(BaseModel):
    """Агрегированная статистика по текущим статусам задач."""

    status: str
    total: int


class TaskTypeObservabilityStat(BaseModel):
    """Dashboard-friendly агрегаты по task type."""

    task_type: str
    total: int
    async_total: int = 0
    completed_total: int = 0
    failed_total: int = 0
    avg_duration_ms: int | None = None
    avg_queue_wait_ms: int | None = None


class TaskObservabilitySummary(BaseModel):
    """Сводка по execution plane поверх task registry."""

    total_tasks: int
    queued_tasks: int = 0
    running_tasks: int = 0
    waiting_human_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    async_tasks: int = 0
    avg_duration_ms: int | None = None
    max_duration_ms: int | None = None
    avg_queue_wait_ms: int | None = None
    statuses: list[TaskStatusStat] = Field(default_factory=list)
    task_types: list[TaskTypeObservabilityStat] = Field(default_factory=list)


class TaskCursor(BaseModel):
    """Декодированное значение курсора истории задач."""

    updated_at: datetime
    task_id: str


class TaskEventCursor(BaseModel):
    """Декодированное значение курсора task events."""

    created_at: datetime
    event_id: int


@runtime_checkable
class TaskRegistry(Protocol):
    """Контракт хранилища lifecycle-записей задач."""

    def save(self, record: TaskRecord) -> None:
        """Сохраняет или обновляет запись задачи."""

    def record_event(self, record: TaskEventRecord) -> None:
        """Сохраняет audit event без изменения task row."""

    def get(self, task_id: str) -> TaskRecord:
        """Возвращает запись задачи по идентификатору."""

    def list_tasks(
        self,
        *,
        limit: int = 50,
        cursor: str | None = None,
        status: str | None = None,
        task_type: str | None = None,
        updated_from: datetime | None = None,
        updated_to: datetime | None = None,
    ) -> TaskListPage:
        """Возвращает историю задач в порядке убывания updated_at/task_id."""

    def list_task_events(
        self,
        *,
        limit: int = 100,
        cursor: str | None = None,
        task_id: str | None = None,
        task_type: str | None = None,
        from_status: str | None = None,
        to_status: str | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
    ) -> TaskEventListPage:
        """Возвращает события аудита переходов статусов."""

    def summarize_task_events(
        self,
        *,
        task_id: str | None = None,
        task_type: str | None = None,
        from_status: str | None = None,
        to_status: str | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
    ) -> TaskEventSummary:
        """Возвращает агрегированную сводку по переходам статусов."""

    def summarize_tasks(
        self,
        *,
        status: str | None = None,
        task_type: str | None = None,
        updated_from: datetime | None = None,
        updated_to: datetime | None = None,
    ) -> TaskObservabilitySummary:
        """Возвращает observability aggregates по task registry."""


class InMemoryTaskRegistry(TaskRegistry):
    """Простая in-memory регистрация задач для API слоя."""

    def __init__(self) -> None:
        self._tasks: dict[str, TaskRecord] = {}
        self._events: list[TaskEventRecord] = []

    def summarize_tasks(
        self,
        *,
        status: str | None = None,
        task_type: str | None = None,
        updated_from: datetime | None = None,
        updated_to: datetime | None = None,
    ) -> TaskObservabilitySummary:
        filtered = _filter_tasks_for_summary(
            self._tasks.values(),
            status=status,
            task_type=task_type,
            updated_from=updated_from,
            updated_to=updated_to,
        )
        return _build_task_observability_summary(filtered)

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

        saved_record = record.model_copy(update={"created_at": created_at, "updated_at": updated_at})
        self._tasks[record.task_id] = saved_record
        self._register_status_event(previous=current, current=saved_record)

    def record_event(self, record: TaskEventRecord) -> None:
        now_utc = datetime.now(timezone.utc)
        event = record.model_copy(
            update={
                "event_id": record.event_id or len(self._events) + 1,
                "created_at": record.created_at or now_utc,
            }
        )
        self._events.append(event)

    def get(self, task_id: str) -> TaskRecord:
        item = self._tasks.get(task_id)
        if item is None:
            raise TaskNotFoundError(f"Задача {task_id} не найдена")
        return item

    def list_tasks(
        self,
        *,
        limit: int = 50,
        cursor: str | None = None,
        status: str | None = None,
        task_type: str | None = None,
        updated_from: datetime | None = None,
        updated_to: datetime | None = None,
    ) -> TaskListPage:
        cursor_payload = decode_task_cursor(cursor) if cursor else None
        normalized_from = _normalize_datetime(updated_from) if updated_from else None
        normalized_to = _normalize_datetime(updated_to) if updated_to else None

        filtered: list[TaskRecord] = []
        for item in self._tasks.values():
            if status and item.status != status:
                continue
            if task_type and item.task_type != task_type:
                continue

            item_updated_at = _effective_task_timestamp(item)
            if normalized_from and item_updated_at < normalized_from:
                continue
            if normalized_to and item_updated_at > normalized_to:
                continue
            if cursor_payload and not _is_before_cursor(item, cursor_payload):
                continue
            filtered.append(item)

        ordered = sorted(filtered, key=lambda task: (_effective_task_timestamp(task), task.task_id), reverse=True)
        window = ordered[: limit + 1]
        has_more = len(window) > limit
        items = window[:limit]
        next_cursor = build_task_cursor(items[-1]) if has_more and items else None

        return TaskListPage(
            items=items,
            limit=limit,
            total_returned=len(items),
            next_cursor=next_cursor,
            has_more=has_more,
        )

    def list_task_events(
        self,
        *,
        limit: int = 100,
        cursor: str | None = None,
        task_id: str | None = None,
        task_type: str | None = None,
        from_status: str | None = None,
        to_status: str | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
    ) -> TaskEventListPage:
        cursor_payload = decode_task_event_cursor(cursor) if cursor else None
        normalized_from = _normalize_datetime(created_from) if created_from else None
        normalized_to = _normalize_datetime(created_to) if created_to else None

        filtered: list[TaskEventRecord] = []
        for item in self._events:
            if task_id and item.task_id != task_id:
                continue
            if task_type and item.task_type != task_type:
                continue
            if from_status is not None and item.from_status != from_status:
                continue
            if to_status and item.to_status != to_status:
                continue

            item_created_at = _effective_event_timestamp(item)
            if normalized_from and item_created_at < normalized_from:
                continue
            if normalized_to and item_created_at > normalized_to:
                continue
            if cursor_payload and not _is_before_event_cursor(item, cursor_payload):
                continue
            filtered.append(item)

        ordered = sorted(
            filtered,
            key=lambda event: (_effective_event_timestamp(event), event.event_id or 0),
            reverse=True,
        )
        window = ordered[: limit + 1]
        has_more = len(window) > limit
        items = window[:limit]
        next_cursor = build_task_event_cursor(items[-1]) if has_more and items else None

        return TaskEventListPage(
            items=items,
            limit=limit,
            total_returned=len(items),
            next_cursor=next_cursor,
            has_more=has_more,
        )

    def summarize_task_events(
        self,
        *,
        task_id: str | None = None,
        task_type: str | None = None,
        from_status: str | None = None,
        to_status: str | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
    ) -> TaskEventSummary:
        normalized_from = _normalize_datetime(created_from) if created_from else None
        normalized_to = _normalize_datetime(created_to) if created_to else None

        filtered: list[TaskEventRecord] = []
        for item in self._events:
            if task_id and item.task_id != task_id:
                continue
            if task_type and item.task_type != task_type:
                continue
            if from_status is not None and item.from_status != from_status:
                continue
            if to_status and item.to_status != to_status:
                continue

            item_created_at = _effective_event_timestamp(item)
            if normalized_from and item_created_at < normalized_from:
                continue
            if normalized_to and item_created_at > normalized_to:
                continue
            filtered.append(item)

        buckets: dict[tuple[str | None, str], int] = {}
        for item in filtered:
            key = (item.from_status, item.to_status)
            buckets[key] = buckets.get(key, 0) + 1

        transitions = [
            TaskEventTransitionStat(from_status=from_status_key, to_status=to_status_key, total=total)
            for (from_status_key, to_status_key), total in buckets.items()
        ]
        transitions.sort(key=lambda item: (-item.total, item.to_status, item.from_status or ""))

        return TaskEventSummary(
            total_events=len(filtered),
            unique_tasks=len({item.task_id for item in filtered}),
            transitions=transitions,
        )

    def _register_status_event(self, *, previous: TaskRecord | None, current: TaskRecord) -> None:
        # Для аудита пишем событие только при создании или реальной смене статуса.
        if previous is not None and previous.status == current.status:
            return

        event = TaskEventRecord(
            event_id=len(self._events) + 1,
            task_id=current.task_id,
            task_type=current.task_type,
            from_status=previous.status if previous else None,
            to_status=current.status,
            from_current_node=previous.current_node if previous else None,
            to_current_node=current.current_node,
            event_payload={"details": current.details},
            created_at=current.updated_at or datetime.now(timezone.utc),
        )
        self._events.append(event)


class TaskApplicationService:
    """Сервис управления состоянием задач и checkpoint payload."""

    def __init__(self, registry: TaskRegistry, checkpoint_store: ICheckpointStore) -> None:
        self._registry = registry
        self._checkpoint_store = checkpoint_store

    def create_task(
        self,
        task_type: str,
        *,
        initial_status: str = "running",
        initial_node: str = "start",
        details: dict | None = None,
    ) -> TaskRecord:
        now_utc = datetime.now(timezone.utc)
        payload = dict(details or {})
        payload.setdefault("correlation_id", payload.get("correlation_id") or str(uuid4()))
        payload.setdefault("async_provider", os.getenv("APP_ASYNC_PROVIDER", "inline").strip().lower() or "inline")
        payload.setdefault("task_type", task_type)
        task = TaskRecord(
            task_id=str(uuid4()),
            task_type=task_type,
            status=initial_status,
            current_node=initial_node,
            details=payload,
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
        current = self._registry.get(task_id)
        return self.update_task(
            task_id,
            status="failed",
            current_node="failed",
            details={**current.details, "error": error_message},
        )

    def update_task(self, task_id: str, **kwargs) -> TaskRecord:
        task = self._registry.get(task_id)
        details = kwargs.get("details")
        if isinstance(details, dict):
            merged_details = dict(details)
        else:
            merged_details = dict(task.details)
        target_status = str(kwargs.get("status", task.status))
        self._enrich_execution_details(task, merged_details, target_status=target_status)
        payload = {
            **kwargs,
            "details": merged_details,
            "created_at": task.created_at,
            "updated_at": datetime.now(timezone.utc),
        }
        updated = task.model_copy(update=payload)
        self._registry.save(updated)
        return updated

    def record_task_event(
        self,
        *,
        task_id: str,
        from_status: str | None,
        to_status: str,
        from_current_node: str | None = None,
        to_current_node: str | None = None,
        event_payload: dict | None = None,
    ) -> TaskEventRecord:
        task = self._registry.get(task_id)
        event = TaskEventRecord(
            task_id=task.task_id,
            task_type=task.task_type,
            from_status=from_status,
            to_status=to_status,
            from_current_node=from_current_node,
            to_current_node=to_current_node,
            event_payload=event_payload or {},
        )
        self._registry.record_event(event)
        return event

    def build_workflow_node_event_sink(self) -> WorkflowNodeEventSink:
        return TaskWorkflowNodeEventSink(self)

    def get_task(self, task_id: str) -> TaskRecord:
        return self._registry.get(task_id)

    def list_tasks(
        self,
        *,
        limit: int = 50,
        cursor: str | None = None,
        status: str | None = None,
        task_type: str | None = None,
        updated_from: datetime | None = None,
        updated_to: datetime | None = None,
    ) -> TaskListPage:
        return self._registry.list_tasks(
            limit=limit,
            cursor=cursor,
            status=status,
            task_type=task_type,
            updated_from=updated_from,
            updated_to=updated_to,
        )

    def list_task_events(
        self,
        *,
        limit: int = 100,
        cursor: str | None = None,
        task_id: str | None = None,
        task_type: str | None = None,
        from_status: str | None = None,
        to_status: str | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
    ) -> TaskEventListPage:
        return self._registry.list_task_events(
            limit=limit,
            cursor=cursor,
            task_id=task_id,
            task_type=task_type,
            from_status=from_status,
            to_status=to_status,
            created_from=created_from,
            created_to=created_to,
        )

    def summarize_task_events(
        self,
        *,
        task_id: str | None = None,
        task_type: str | None = None,
        from_status: str | None = None,
        to_status: str | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
    ) -> TaskEventSummary:
        return self._registry.summarize_task_events(
            task_id=task_id,
            task_type=task_type,
            from_status=from_status,
            to_status=to_status,
            created_from=created_from,
            created_to=created_to,
        )

    def summarize_tasks(
        self,
        *,
        status: str | None = None,
        task_type: str | None = None,
        updated_from: datetime | None = None,
        updated_to: datetime | None = None,
    ) -> TaskObservabilitySummary:
        return self._registry.summarize_tasks(
            status=status,
            task_type=task_type,
            updated_from=updated_from,
            updated_to=updated_to,
        )

    def get_state_payload(self, task_id: str) -> dict:
        payload = self._checkpoint_store.load_checkpoint(task_id)
        if payload is None:
            raise TaskNotFoundError(f"Checkpoint для задачи {task_id} не найден")
        return payload

    def get_langgraph_checkpointer(self) -> Any | None:
        """Возвращает checkpointer для LangGraph, если текущий store его поддерживает."""

        builder = getattr(self._checkpoint_store, "build_langgraph_checkpointer", None)
        if callable(builder):
            return builder()
        return None

    def _enrich_execution_details(self, current: TaskRecord, details: dict, *, target_status: str) -> None:
        details.setdefault("correlation_id", current.details.get("correlation_id") or str(uuid4()))
        details.setdefault(
            "async_provider",
            current.details.get("async_provider") or (os.getenv("APP_ASYNC_PROVIDER", "inline").strip().lower() or "inline"),
        )
        details.setdefault("task_type", current.task_type)

        if current.details.get("queued_at") and not details.get("queued_at"):
            details["queued_at"] = current.details.get("queued_at")
        if current.details.get("started_at") and not details.get("started_at"):
            details["started_at"] = current.details.get("started_at")
        if current.details.get("completed_at") and not details.get("completed_at"):
            details["completed_at"] = current.details.get("completed_at")
        if current.details.get("failed_at") and not details.get("failed_at"):
            details["failed_at"] = current.details.get("failed_at")

        now_iso = datetime.now(timezone.utc).isoformat()
        execution_mode = str(details.get("execution_mode", current.details.get("execution_mode", "sync")))
        if details.get("queued_at") is None and execution_mode == "async":
            details["queued_at"] = current.created_at.isoformat() if current.created_at else now_iso
        if details.get("started_at") is None and current.status == "queued" and target_status != "queued":
            details["started_at"] = now_iso
        if details.get("completed_at") is None and target_status == "completed":
            details["completed_at"] = now_iso
        if details.get("failed_at") is None and target_status == "failed":
            details["failed_at"] = now_iso

        if details.get("started_at") and details.get("queued_at") and details.get("queue_wait_ms") is None:
            queue_wait_ms = _duration_ms_from_iso(details.get("queued_at"), details.get("started_at"))
            if queue_wait_ms is not None:
                details["queue_wait_ms"] = queue_wait_ms


class TaskWorkflowNodeEventSink:
    """Maps framework workflow node events into task_events audit records."""

    def __init__(self, task_service: TaskApplicationService) -> None:
        self._task_service = task_service

    def record_node_event(self, event: WorkflowNodeEventRecord) -> None:
        if not event.task_id:
            return

        task = self._task_service.get_task(event.task_id)
        self._task_service.record_task_event(
            task_id=task.task_id,
            from_status=task.status,
            to_status=task.status,
            from_current_node=task.current_node,
            to_current_node=event.node_name,
            event_payload={
                "event_kind": "workflow_node",
                "workflow_name": event.workflow_name,
                "node_name": event.node_name,
                "node_status": event.status,
                "is_resume": event.is_resume,
                "correlation_id": event.correlation_id,
                "metadata": event.metadata,
                **({"error": event.error} if event.error else {}),
            },
        )


def build_task_cursor(task: TaskRecord) -> str:
    """Строит opaque-курсор из позиции задачи в сортировке истории."""

    payload = {
        "updated_at": _effective_task_timestamp(task).isoformat(),
        "task_id": task.task_id,
    }
    raw = json.dumps(payload, ensure_ascii=True, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def decode_task_cursor(cursor: str) -> TaskCursor:
    """Декодирует opaque-курсор истории задач и валидирует его структуру."""

    payload = _decode_base64_payload(cursor)
    updated_at_raw = payload.get("updated_at")
    task_id = payload.get("task_id")
    if not isinstance(updated_at_raw, str) or not isinstance(task_id, str) or not task_id:
        raise InvalidCursorError("Cursor должен содержать updated_at и task_id")

    try:
        updated_at = datetime.fromisoformat(updated_at_raw)
    except ValueError as exc:
        raise InvalidCursorError("Cursor содержит некорректное значение updated_at") from exc

    return TaskCursor(updated_at=_normalize_datetime(updated_at), task_id=task_id)


def build_task_event_cursor(event: TaskEventRecord) -> str:
    """Строит opaque-курсор из позиции события в сортировке аудита."""

    event_id = event.event_id
    if event_id is None:
        raise InvalidCursorError("Невозможно построить cursor без event_id")

    payload = {
        "created_at": _effective_event_timestamp(event).isoformat(),
        "event_id": event_id,
    }
    raw = json.dumps(payload, ensure_ascii=True, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def decode_task_event_cursor(cursor: str) -> TaskEventCursor:
    """Декодирует opaque-курсор task events и валидирует его структуру."""

    payload = _decode_base64_payload(cursor)
    created_at_raw = payload.get("created_at")
    event_id_raw = payload.get("event_id")

    if not isinstance(created_at_raw, str):
        raise InvalidCursorError("Cursor должен содержать created_at")
    if not isinstance(event_id_raw, int):
        raise InvalidCursorError("Cursor должен содержать числовой event_id")

    try:
        created_at = datetime.fromisoformat(created_at_raw)
    except ValueError as exc:
        raise InvalidCursorError("Cursor содержит некорректное значение created_at") from exc

    return TaskEventCursor(created_at=_normalize_datetime(created_at), event_id=event_id_raw)


def _decode_base64_payload(cursor: str) -> dict:
    try:
        padding = "=" * (-len(cursor) % 4)
        decoded = base64.urlsafe_b64decode((cursor + padding).encode("ascii")).decode("utf-8")
        payload = json.loads(decoded)
    except Exception as exc:  # pragma: no cover - защитная ветка
        raise InvalidCursorError("Некорректный формат cursor") from exc

    if not isinstance(payload, dict):
        raise InvalidCursorError("Cursor должен декодироваться в JSON-объект")
    return payload


def _effective_task_timestamp(task: TaskRecord) -> datetime:
    return _normalize_datetime(task.updated_at or task.created_at or datetime.min.replace(tzinfo=timezone.utc))


def _effective_event_timestamp(event: TaskEventRecord) -> datetime:
    return _normalize_datetime(event.created_at or datetime.min.replace(tzinfo=timezone.utc))


def _normalize_datetime(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _is_before_cursor(task: TaskRecord, cursor: TaskCursor) -> bool:
    task_timestamp = _effective_task_timestamp(task)
    if task_timestamp < cursor.updated_at:
        return True
    if task_timestamp > cursor.updated_at:
        return False
    return task.task_id < cursor.task_id


def _is_before_event_cursor(event: TaskEventRecord, cursor: TaskEventCursor) -> bool:
    event_timestamp = _effective_event_timestamp(event)
    if event_timestamp < cursor.created_at:
        return True
    if event_timestamp > cursor.created_at:
        return False
    return (event.event_id or 0) < cursor.event_id


def _filter_tasks_for_summary(
    tasks: list[TaskRecord] | tuple[TaskRecord, ...] | Any,
    *,
    status: str | None = None,
    task_type: str | None = None,
    updated_from: datetime | None = None,
    updated_to: datetime | None = None,
) -> list[TaskRecord]:
    normalized_from = _normalize_datetime(updated_from) if updated_from else None
    normalized_to = _normalize_datetime(updated_to) if updated_to else None
    filtered: list[TaskRecord] = []
    for item in tasks:
        if status and item.status != status:
            continue
        if task_type and item.task_type != task_type:
            continue
        item_updated_at = _effective_task_timestamp(item)
        if normalized_from and item_updated_at < normalized_from:
            continue
        if normalized_to and item_updated_at > normalized_to:
            continue
        filtered.append(item)
    return filtered


def _build_task_observability_summary(tasks: list[TaskRecord]) -> TaskObservabilitySummary:
    status_buckets: dict[str, int] = {}
    type_buckets: dict[str, dict[str, Any]] = {}
    durations: list[int] = []
    queue_waits: list[int] = []

    for task in tasks:
        status_buckets[task.status] = status_buckets.get(task.status, 0) + 1
        task_durations = _task_duration_ms(task)
        if task_durations is not None:
            durations.append(task_durations)
        task_queue_wait = _task_queue_wait_ms(task)
        if task_queue_wait is not None:
            queue_waits.append(task_queue_wait)

        bucket = type_buckets.setdefault(
            task.task_type,
            {
                "total": 0,
                "async_total": 0,
                "completed_total": 0,
                "failed_total": 0,
                "durations": [],
                "queue_waits": [],
            },
        )
        bucket["total"] += 1
        if str(task.details.get("execution_mode", "sync")) == "async":
            bucket["async_total"] += 1
        if task.status == "completed":
            bucket["completed_total"] += 1
        if task.status == "failed":
            bucket["failed_total"] += 1
        if task_durations is not None:
            bucket["durations"].append(task_durations)
        if task_queue_wait is not None:
            bucket["queue_waits"].append(task_queue_wait)

    status_items = [TaskStatusStat(status=name, total=total) for name, total in status_buckets.items()]
    status_items.sort(key=lambda item: (-item.total, item.status))

    task_type_items: list[TaskTypeObservabilityStat] = []
    for task_type, bucket in type_buckets.items():
        task_type_items.append(
            TaskTypeObservabilityStat(
                task_type=task_type,
                total=int(bucket["total"]),
                async_total=int(bucket["async_total"]),
                completed_total=int(bucket["completed_total"]),
                failed_total=int(bucket["failed_total"]),
                avg_duration_ms=_avg_int(bucket["durations"]),
                avg_queue_wait_ms=_avg_int(bucket["queue_waits"]),
            )
        )
    task_type_items.sort(key=lambda item: (-item.total, item.task_type))

    return TaskObservabilitySummary(
        total_tasks=len(tasks),
        queued_tasks=status_buckets.get("queued", 0),
        running_tasks=status_buckets.get("running", 0),
        waiting_human_tasks=status_buckets.get("waiting_human", 0),
        completed_tasks=status_buckets.get("completed", 0),
        failed_tasks=status_buckets.get("failed", 0),
        async_tasks=sum(1 for task in tasks if str(task.details.get("execution_mode", "sync")) == "async"),
        avg_duration_ms=_avg_int(durations),
        max_duration_ms=max(durations) if durations else None,
        avg_queue_wait_ms=_avg_int(queue_waits),
        statuses=status_items,
        task_types=task_type_items,
    )


def _task_duration_ms(task: TaskRecord) -> int | None:
    if task.created_at is None or task.updated_at is None:
        return None
    created = _normalize_datetime(task.created_at)
    updated = _normalize_datetime(task.updated_at)
    return max(0, int((updated - created).total_seconds() * 1000))


def _task_queue_wait_ms(task: TaskRecord) -> int | None:
    value = task.details.get("queue_wait_ms")
    if isinstance(value, int):
        return max(0, value)
    if isinstance(value, float):
        return max(0, int(value))
    return None


def _avg_int(values: list[int]) -> int | None:
    if not values:
        return None
    return int(sum(values) / len(values))


def _duration_ms_from_iso(start_raw: Any, end_raw: Any) -> int | None:
    if not isinstance(start_raw, str) or not isinstance(end_raw, str):
        return None
    try:
        start = _normalize_datetime(datetime.fromisoformat(start_raw))
        end = _normalize_datetime(datetime.fromisoformat(end_raw))
    except ValueError:
        return None
    return max(0, int((end - start).total_seconds() * 1000))
