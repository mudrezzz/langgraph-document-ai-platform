from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class IHumanReviewPort(Protocol):
    """Контракт взаимодействия с human review boundary."""

    def request_review(self, payload: dict[str, Any]) -> str:
        """Создает задачу на ручной review."""

    def resolve_review(self, review_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Получает решение по review-задаче."""
