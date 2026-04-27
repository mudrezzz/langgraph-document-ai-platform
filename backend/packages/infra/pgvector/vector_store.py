from __future__ import annotations

import json
import math
from dataclasses import dataclass
from typing import Any

from framework.stores.interfaces import IVectorStore
from infra.postgres.config import PostgresSettings, validate_identifier


@dataclass(slots=True)
class VectorSearchResult:
    """Search result returned by vector store."""

    key: str
    score: float
    metadata: dict[str, Any]


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
        use_fallback_if_unset: bool | None = None,
    ) -> "PgVectorStoreAdapter":
        fallback_enabled = settings.allow_fallback_persistence if use_fallback_if_unset is None else use_fallback_if_unset
        return cls(dsn=settings.dsn, schema=settings.schema, use_fallback_if_unset=fallback_enabled)

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

    def delete_vectors(self, *, metadata_filter: dict[str, Any]) -> int:
        """Deletes vectors matching metadata filter and returns deleted count."""

        if not metadata_filter:
            raise ValueError("metadata_filter обязателен для delete_vectors")

        if self._use_fallback:
            stale_keys = [key for key, (_, metadata) in self._storage.items() if _metadata_matches(metadata, metadata_filter)]
            for key in stale_keys:
                del self._storage[key]
            return len(stale_keys)

        psycopg, dict_row = _import_psycopg()
        metadata_json = json.dumps(metadata_filter, ensure_ascii=False)
        with psycopg.connect(self._dsn, autocommit=True, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"DELETE FROM {self._schema}.embeddings WHERE metadata @> %s::jsonb",
                    (metadata_json,),
                )
                return int(cur.rowcount or 0)

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

    def query_similar(
        self,
        vector: list[float],
        *,
        limit: int = 20,
        metadata_filter: dict[str, Any] | None = None,
    ) -> list[VectorSearchResult]:
        """Returns nearest vectors ordered by cosine similarity."""

        if limit < 1:
            raise ValueError("limit должен быть >= 1")

        if self._use_fallback:
            candidates: list[VectorSearchResult] = []
            for key, (stored_vector, metadata) in self._storage.items():
                if metadata_filter and not _metadata_matches(metadata, metadata_filter):
                    continue
                candidates.append(
                    VectorSearchResult(
                        key=key,
                        score=_cosine_similarity(vector, stored_vector),
                        metadata=dict(metadata),
                    )
                )
            return sorted(candidates, key=lambda item: item.score, reverse=True)[:limit]

        psycopg, dict_row = _import_psycopg()
        vector_literal = _vector_to_literal(vector)
        metadata_json = json.dumps(metadata_filter or {}, ensure_ascii=False)

        with psycopg.connect(self._dsn, autocommit=True, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    SELECT vector_key, 1.0 / (1.0 + (embedding <=> %s::vector)) AS score, metadata
                    FROM {self._schema}.embeddings
                    WHERE metadata @> %s::jsonb
                    ORDER BY embedding <=> %s::vector
                    LIMIT %s
                    """,
                    (vector_literal, metadata_json, vector_literal, limit),
                )
                rows = cur.fetchall()

        return [
            VectorSearchResult(
                key=row["vector_key"],
                score=float(row["score"]),
                metadata=json.loads(row["metadata"]) if isinstance(row["metadata"], str) else row["metadata"],
            )
            for row in rows
        ]


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


def _cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    dot = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if left_norm <= 0 or right_norm <= 0:
        return 0.0
    return dot / (left_norm * right_norm)


def _metadata_matches(metadata: dict[str, Any], expected: dict[str, Any]) -> bool:
    for key, value in expected.items():
        if metadata.get(key) != value:
            return False
    return True


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
