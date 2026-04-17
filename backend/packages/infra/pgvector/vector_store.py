from __future__ import annotations

from framework.stores.interfaces import IVectorStore


class PgVectorStoreAdapter(IVectorStore):
    """Скелет адаптера векторного хранилища поверх pgvector."""

    def __init__(self) -> None:
        self._storage: dict[str, tuple[list[float], dict]] = {}

    def upsert_vector(self, key: str, vector: list[float], metadata: dict) -> None:
        # В инкременте 2 используем in-memory слой вместо реального PostgreSQL.
        self._storage[key] = (vector, metadata)

    def get_vector(self, key: str) -> tuple[list[float], dict] | None:
        return self._storage.get(key)