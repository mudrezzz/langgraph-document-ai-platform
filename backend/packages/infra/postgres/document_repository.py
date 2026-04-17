from __future__ import annotations

from typing import Any

from framework.db.repository import BaseRepository
from framework.stores.interfaces import IDocumentStore


class PostgresDocumentRepository(BaseRepository, IDocumentStore):
    """Скелет репозитория документов (PostgreSQL adapter)."""

    def __init__(self) -> None:
        self._storage: dict[str, dict[str, Any]] = {}

    def get(self, entity_id: str) -> dict[str, Any] | None:
        return self._storage.get(entity_id)

    def save(self, payload: dict[str, Any]) -> str:
        entity_id = str(payload.get("doc_id") or payload.get("id") or len(self._storage) + 1)
        self._storage[entity_id] = payload
        return entity_id

    def read_document(self, doc_id: str) -> dict[str, Any]:
        value = self._storage.get(doc_id)
        if value is None:
            raise KeyError(f"Документ {doc_id} не найден")
        return value