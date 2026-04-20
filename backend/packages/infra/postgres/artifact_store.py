from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from framework.stores.base import BaseArtifactStore
from infra.postgres.config import PostgresSettings, validate_identifier


class PostgresArtifactStore(BaseArtifactStore):
    """Хранилище артефактов поверх PostgreSQL с in-memory fallback."""

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
            raise ValueError("DSN обязателен для PostgreSQL artifact store")

    @classmethod
    def from_settings(
        cls,
        settings: PostgresSettings,
        *,
        use_fallback_if_unset: bool | None = None,
    ) -> "PostgresArtifactStore":
        fallback_enabled = settings.allow_fallback_persistence if use_fallback_if_unset is None else use_fallback_if_unset
        return cls(dsn=settings.dsn, schema=settings.schema, use_fallback_if_unset=fallback_enabled)

    def save_artifact(self, artifact_id: str, payload: dict[str, Any]) -> None:
        artifact_type = str(payload.get("artifact_type", "generic"))

        if self._use_fallback:
            now_utc = datetime.now(timezone.utc)
            current = self._storage.get(artifact_id)
            self._storage[artifact_id] = {
                "payload": dict(payload),
                "artifact_type": artifact_type,
                "created_at": current["created_at"] if current else now_utc,
                "updated_at": now_utc,
            }
            return

        psycopg, dict_row = _import_psycopg()
        payload_json = json.dumps(payload, ensure_ascii=False)

        with psycopg.connect(self._dsn, autocommit=True, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    INSERT INTO {self._schema}.artifacts (artifact_id, artifact_type, payload)
                    VALUES (%s, %s, %s::jsonb)
                    ON CONFLICT (artifact_id)
                    DO UPDATE SET
                        artifact_type = EXCLUDED.artifact_type,
                        payload = EXCLUDED.payload,
                        updated_at = now()
                    """,
                    (artifact_id, artifact_type, payload_json),
                )

    def read_artifact(self, artifact_id: str) -> dict[str, Any]:
        if self._use_fallback:
            item = self._storage.get(artifact_id)
            if item is None:
                raise KeyError(f"Артефакт {artifact_id} не найден")
            return dict(item["payload"])

        psycopg, dict_row = _import_psycopg()
        with psycopg.connect(self._dsn, autocommit=True, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"SELECT payload FROM {self._schema}.artifacts WHERE artifact_id = %s",
                    (artifact_id,),
                )
                row = cur.fetchone()

        if row is None:
            raise KeyError(f"Артефакт {artifact_id} не найден")

        payload = row["payload"]
        if isinstance(payload, str):
            return json.loads(payload)
        return payload

    def list_artifacts(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
        artifact_type: str | None = None,
    ) -> list[dict[str, Any]]:
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
            if artifact_type:
                ordered = [item for item in ordered if item[1]["artifact_type"] == artifact_type]
            window = ordered[offset : offset + limit]
            return [
                {
                    "artifact_id": artifact_id,
                    "artifact_type": item["artifact_type"],
                    "payload": dict(item["payload"]),
                    "created_at": item["created_at"],
                    "updated_at": item["updated_at"],
                }
                for artifact_id, item in window
            ]

        where_clause = "artifact_type = %s" if artifact_type else "1=1"
        params: list[object] = [limit, offset]
        if artifact_type:
            params = [artifact_type, limit, offset]

        psycopg, dict_row = _import_psycopg()
        with psycopg.connect(self._dsn, autocommit=True, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    SELECT artifact_id, artifact_type, payload, created_at, updated_at
                    FROM {self._schema}.artifacts
                    WHERE {where_clause}
                    ORDER BY updated_at DESC, artifact_id DESC
                    LIMIT %s
                    OFFSET %s
                    """,
                    tuple(params),
                )
                rows = cur.fetchall()

        result: list[dict[str, Any]] = []
        for row in rows:
            payload = row["payload"]
            if isinstance(payload, str):
                payload = json.loads(payload)
            result.append(
                {
                    "artifact_id": row["artifact_id"],
                    "artifact_type": row["artifact_type"],
                    "payload": payload,
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"],
                }
            )
        return result


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
