from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class IRepository(Protocol):
    """Базовый репозиторный контракт."""

    def get(self, entity_id: str) -> dict[str, Any] | None:
        """Возвращает сущность по идентификатору."""

    def save(self, payload: dict[str, Any]) -> str:
        """Сохраняет сущность и возвращает ее идентификатор."""


@runtime_checkable
class UnitOfWork(Protocol):
    """Контракт транзакционной границы."""

    def __enter__(self) -> "UnitOfWork":
        """Открывает транзакционный контекст."""

    def __exit__(self, exc_type, exc, tb) -> None:
        """Завершает транзакционный контекст."""

    def commit(self) -> None:
        """Подтверждает транзакцию."""

    def rollback(self) -> None:
        """Откатывает транзакцию."""
