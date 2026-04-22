from __future__ import annotations

import base64
import json
from datetime import datetime, timezone
from typing import Protocol, runtime_checkable

from pydantic import BaseModel, Field

from application.errors import InvalidCursorError, TaskNotFoundError


class HitlActionRecord(BaseModel):
    """Запись действия reviewer в HITL контуре."""

    action_id: str
    task_id: str
    iteration: int
    decision: str
    status: str
    comment: str | None = None
    reviewer: str | None = None
    idempotency_key: str | None = None
    metadata: dict = Field(default_factory=dict)
    created_at: datetime | None = None
    updated_at: datetime | None = None


class HitlActionListPage(BaseModel):
    """Страница HITL действий с курсорной пагинацией."""

    items: list[HitlActionRecord] = Field(default_factory=list)
    limit: int
    total_returned: int
    next_cursor: str | None = None
    has_more: bool = False


class HitlActionCursor(BaseModel):
    """Декодированное значение курсора HITL действий."""

    created_at: datetime
    action_id: str


@runtime_checkable
class HitlActionStore(Protocol):
    """Контракт persistence/read-model для HITL reviewer actions."""

    def save_action(self, record: HitlActionRecord) -> None:
        """Создает или обновляет HITL action запись."""

    def get_action(self, action_id: str) -> HitlActionRecord:
        """Возвращает действие по идентификатору."""

    def list_actions(
        self,
        *,
        limit: int = 50,
        cursor: str | None = None,
        task_id: str | None = None,
        decision: str | None = None,
        status: str | None = None,
        reviewer: str | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
    ) -> HitlActionListPage:
        """Возвращает историю HITL действий по фильтрам."""


class InMemoryHitlActionStore(HitlActionStore):
    """In-memory хранилище HITL действий для dev/test fallback."""

    def __init__(self) -> None:
        self._actions: dict[str, HitlActionRecord] = {}

    def save_action(self, record: HitlActionRecord) -> None:
        now_utc = datetime.now(timezone.utc)
        current = self._actions.get(record.action_id)
        created_at = current.created_at if current else (record.created_at or now_utc)
        self._actions[record.action_id] = record.model_copy(
            update={
                "created_at": created_at,
                "updated_at": now_utc,
            }
        )

    def get_action(self, action_id: str) -> HitlActionRecord:
        action = self._actions.get(action_id)
        if action is None:
            raise TaskNotFoundError(f"HITL action {action_id} не найден")
        return action

    def list_actions(
        self,
        *,
        limit: int = 50,
        cursor: str | None = None,
        task_id: str | None = None,
        decision: str | None = None,
        status: str | None = None,
        reviewer: str | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
    ) -> HitlActionListPage:
        cursor_payload = decode_hitl_action_cursor(cursor) if cursor else None
        normalized_from = _normalize_datetime(created_from) if created_from else None
        normalized_to = _normalize_datetime(created_to) if created_to else None

        filtered: list[HitlActionRecord] = []
        for item in self._actions.values():
            if task_id and item.task_id != task_id:
                continue
            if decision and item.decision != decision:
                continue
            if status and item.status != status:
                continue
            if reviewer and item.reviewer != reviewer:
                continue

            item_created_at = _effective_hitl_timestamp(item)
            if normalized_from and item_created_at < normalized_from:
                continue
            if normalized_to and item_created_at > normalized_to:
                continue
            if cursor_payload and not _is_before_cursor(item, cursor_payload):
                continue
            filtered.append(item)

        ordered = sorted(
            filtered,
            key=lambda action: (_effective_hitl_timestamp(action), action.action_id),
            reverse=True,
        )
        window = ordered[: limit + 1]
        has_more = len(window) > limit
        items = window[:limit]
        next_cursor = build_hitl_action_cursor(items[-1]) if has_more and items else None
        return HitlActionListPage(
            items=items,
            limit=limit,
            total_returned=len(items),
            next_cursor=next_cursor,
            has_more=has_more,
        )


def build_hitl_action_cursor(action: HitlActionRecord) -> str:
    """Строит opaque-курсор из позиции HITL action в сортировке истории."""

    payload = {
        "created_at": _effective_hitl_timestamp(action).isoformat(),
        "action_id": action.action_id,
    }
    raw = json.dumps(payload, ensure_ascii=True, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def decode_hitl_action_cursor(cursor: str) -> HitlActionCursor:
    """Декодирует opaque-курсор HITL действий и валидирует структуру."""

    payload = _decode_base64_payload(cursor)
    created_at_raw = payload.get("created_at")
    action_id = payload.get("action_id")
    if not isinstance(created_at_raw, str) or not isinstance(action_id, str) or not action_id:
        raise InvalidCursorError("Cursor должен содержать created_at и action_id")

    try:
        created_at = datetime.fromisoformat(created_at_raw)
    except ValueError as exc:
        raise InvalidCursorError("Cursor содержит некорректное значение created_at") from exc

    return HitlActionCursor(created_at=_normalize_datetime(created_at), action_id=action_id)


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


def _normalize_datetime(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _effective_hitl_timestamp(action: HitlActionRecord) -> datetime:
    return _normalize_datetime(action.created_at or action.updated_at or datetime.min.replace(tzinfo=timezone.utc))


def _is_before_cursor(action: HitlActionRecord, cursor: HitlActionCursor) -> bool:
    action_timestamp = _effective_hitl_timestamp(action)
    if action_timestamp < cursor.created_at:
        return True
    if action_timestamp > cursor.created_at:
        return False
    return action.action_id < cursor.action_id
