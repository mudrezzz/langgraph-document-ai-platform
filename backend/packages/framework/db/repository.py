from __future__ import annotations

from typing import Any

from framework.db.interfaces import IRepository, UnitOfWork


class BaseRepository(IRepository):
    """Базовая заглушка репозитория."""

    def get(self, entity_id: str) -> dict[str, Any] | None:
        raise NotImplementedError("BaseRepository.get не реализован")

    def save(self, payload: dict[str, Any]) -> str:
        raise NotImplementedError("BaseRepository.save не реализован")


class RepositoryFactory:
    """Фабрика репозиториев."""

    def __init__(self) -> None:
        self._registry: dict[str, type[IRepository]] = {}

    def register(self, key: str, repo_type: type[IRepository]) -> None:
        self._registry[key] = repo_type

    def build(self, key: str) -> IRepository:
        repo_type = self._registry[key]
        return repo_type()


class DummyUnitOfWork(UnitOfWork):
    """Тестовая реализация UnitOfWork без реальной транзакции."""

    def __enter__(self) -> "DummyUnitOfWork":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if exc_type:
            self.rollback()
        else:
            self.commit()

    def commit(self) -> None:
        return None

    def rollback(self) -> None:
        return None