from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from framework.db.repository import BaseRepository
from framework.stores.interfaces import IDocumentStore
from infra.postgres.config import PostgresSettings, validate_identifier


class PostgresDocumentRepository(BaseRepository, IDocumentStore):
    """Репозиторий документов поверх PostgreSQL с in-memory fallback."""

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
        self._storage: dict[str, dict[str, Any]] = {}

        if not self._use_fallback and not self._dsn:
            raise ValueError("DSN обязателен для PostgreSQL document repository")

    @classmethod
    def from_settings(
        cls,
        settings: PostgresSettings,
        *,
        use_fallback_if_unset: bool | None = None,
    ) -> "PostgresDocumentRepository":
        fallback_enabled = settings.allow_fallback_persistence if use_fallback_if_unset is None else use_fallback_if_unset
        return cls(dsn=settings.dsn, schema=settings.schema, use_fallback_if_unset=fallback_enabled)

    def get(self, entity_id: str) -> dict[str, Any] | None:
        if self._use_fallback:
            item = self._storage.get(entity_id)
            if item is None:
                return None
            return dict(item["payload"])

        psycopg, dict_row = _import_psycopg()

        with psycopg.connect(self._dsn, autocommit=True, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"SELECT payload FROM {self._schema}.documents WHERE doc_id = %s",
                    (entity_id,),
                )
                row = cur.fetchone()

        if row is None:
            return None

        payload = row["payload"]
        if isinstance(payload, str):
            return json.loads(payload)
        return payload

    def save(self, payload: dict[str, Any]) -> str:
        entity_id = str(payload.get("doc_id") or payload.get("id") or len(self._storage) + 1)

        if self._use_fallback:
            now_utc = datetime.now(timezone.utc)
            current = self._storage.get(entity_id)
            self._storage[entity_id] = {
                "payload": dict(payload),
                "created_at": current["created_at"] if current else now_utc,
                "updated_at": now_utc,
            }
            return entity_id

        psycopg, dict_row = _import_psycopg()
        payload_json = json.dumps(payload, ensure_ascii=False)

        with psycopg.connect(self._dsn, autocommit=True, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    INSERT INTO {self._schema}.documents (doc_id, payload)
                    VALUES (%s, %s::jsonb)
                    ON CONFLICT (doc_id)
                    DO UPDATE SET payload = EXCLUDED.payload, updated_at = now()
                    """,
                    (entity_id, payload_json),
                )

        return entity_id

    def list_documents(self, *, limit: int = 50, offset: int = 0) -> list[dict[str, Any]]:
        if limit < 1:
            raise ValueError("limit должен быть >= 1")
        if offset < 0:
            raise ValueError("offset должен быть >= 0")

        if self._use_fallback:
            ordered = sorted(
                self._storage.items(),
                key=lambda item: (item[1]["updated_at"], item[0]),
                reverse=True,
            )
            window = ordered[offset : offset + limit]
            return [
                {
                    "doc_id": doc_id,
                    "payload": dict(item["payload"]),
                    "created_at": item["created_at"],
                    "updated_at": item["updated_at"],
                }
                for doc_id, item in window
            ]

        psycopg, dict_row = _import_psycopg()
        with psycopg.connect(self._dsn, autocommit=True, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    SELECT doc_id, payload, created_at, updated_at
                    FROM {self._schema}.documents
                    ORDER BY updated_at DESC, doc_id DESC
                    LIMIT %s
                    OFFSET %s
                    """,
                    (limit, offset),
                )
                rows = cur.fetchall()

        result: list[dict[str, Any]] = []
        for row in rows:
            payload = row["payload"]
            if isinstance(payload, str):
                payload = json.loads(payload)
            result.append(
                {
                    "doc_id": row["doc_id"],
                    "payload": payload,
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"],
                }
            )
        return result

    def read_document(self, doc_id: str) -> dict[str, Any]:
        value = self.get(doc_id)
        if value is None:
            raise KeyError(f"Документ {doc_id} не найден")
        return value


def _import_psycopg():
    try:
        import psycopg
        from psycopg.rows import dict_row
    except Exception as exc:  # pragma: no cover - зависит от окружения
        raise RuntimeError(
            "Для PostgreSQL режима требуется установленный psycopg. "
            "Установите зависимость 'psycopg[binary]'."
        ) from exc
    return psycopg, dict_row
