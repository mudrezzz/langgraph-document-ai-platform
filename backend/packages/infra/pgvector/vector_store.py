from __future__ import annotations

import json
from typing import Any

from framework.stores.interfaces import IVectorStore
from infra.postgres.config import PostgresSettings, validate_identifier


class PgVectorStoreAdapter(IVectorStore):
    """Адаптер векторного хранилища поверх pgvector с in-memory fallback."""

    def __init__(
        self,
        dsn: str | None = None,
        schema: str = "app",
        *,
        use_fallback_if_unset: bool = True,
    ) -> None:
        self._schema = schema
        validate_identifier(self._schema)

        self._dsn = dsn
        self._use_fallback = use_fallback_if_unset and not bool(dsn)
        self._storage: dict[str, tuple[list[float], dict[str, Any]]] = {}

        if not self._use_fallback and not self._dsn:
            raise ValueError("DSN обязателен для pgvector adapter")

    @classmethod
    def from_settings(
        cls,
        settings: PostgresSettings,
        *,
        use_fallback_if_unset: bool = True,
    ) -> "PgVectorStoreAdapter":
        return cls(dsn=settings.dsn, schema=settings.schema, use_fallback_if_unset=use_fallback_if_unset)

    def upsert_vector(self, key: str, vector: list[float], metadata: dict) -> None:
        if self._use_fallback:
            self._storage[key] = (vector, metadata)
            return

        psycopg, dict_row = _import_psycopg()
        vector_literal = _vector_to_literal(vector)
        metadata_json = json.dumps(metadata, ensure_ascii=False)

        with psycopg.connect(self._dsn, autocommit=True, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    INSERT INTO {self._schema}.embeddings (vector_key, embedding, metadata)
                    VALUES (%s, %s::vector, %s::jsonb)
                    ON CONFLICT (vector_key)
                    DO UPDATE SET embedding = EXCLUDED.embedding, metadata = EXCLUDED.metadata, updated_at = now()
                    """,
                    (key, vector_literal, metadata_json),
                )

    def get_vector(self, key: str) -> tuple[list[float], dict] | None:
        if self._use_fallback:
            return self._storage.get(key)

        psycopg, dict_row = _import_psycopg()

        with psycopg.connect(self._dsn, autocommit=True, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"SELECT embedding::text AS embedding, metadata FROM {self._schema}.embeddings WHERE vector_key = %s",
                    (key,),
                )
                row = cur.fetchone()

        if row is None:
            return None

        embedding_raw = row["embedding"]
        metadata_raw = row["metadata"]

        vector = _parse_vector_text(embedding_raw)
        metadata = json.loads(metadata_raw) if isinstance(metadata_raw, str) else metadata_raw
        return vector, metadata


def _vector_to_literal(vector: list[float]) -> str:
    """Формирует pgvector-совместимый литерал вида `[1,2,3]`."""

    return "[" + ",".join(f"{value:.12g}" for value in vector) + "]"


def _parse_vector_text(raw: str) -> list[float]:
    text = raw.strip()
    if not text.startswith("[") or not text.endswith("]"):
        raise ValueError(f"Некорректное значение vector: {raw}")

    body = text[1:-1].strip()
    if not body:
        return []

    return [float(part.strip()) for part in body.split(",")]


def _import_psycopg():
    try:
        import psycopg
        from psycopg.rows import dict_row
    except Exception as exc:  # pragma: no cover - зависит от окружения
        raise RuntimeError(
            "Для pgvector режима требуется установленный psycopg. "
            "Установите зависимость 'psycopg[binary]'."
        ) from exc
    return psycopg, dict_row