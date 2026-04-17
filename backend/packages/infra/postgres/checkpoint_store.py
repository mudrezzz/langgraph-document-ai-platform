from __future__ import annotations

import json
from typing import Any

from framework.stores.interfaces import ICheckpointStore
from infra.postgres.config import PostgresSettings, validate_identifier


class LangGraphPostgresCheckpointStore(ICheckpointStore):
    """Checkpoint store для LangGraph поверх PostgreSQL с in-memory fallback."""

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
        self._checkpoints: dict[str, dict[str, Any]] = {}

        if not self._use_fallback and not self._dsn:
            raise ValueError("DSN обязателен для PostgreSQL checkpoint store")

    @classmethod
    def from_settings(
        cls,
        settings: PostgresSettings,
        *,
        use_fallback_if_unset: bool = True,
    ) -> "LangGraphPostgresCheckpointStore":
        return cls(dsn=settings.dsn, schema=settings.schema, use_fallback_if_unset=use_fallback_if_unset)

    def save_checkpoint(self, run_id: str, payload: dict) -> None:
        if self._use_fallback:
            self._checkpoints[run_id] = payload
            return

        psycopg, dict_row = _import_psycopg()
        payload_json = json.dumps(payload, ensure_ascii=False)

        with psycopg.connect(self._dsn, autocommit=True, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    INSERT INTO {self._schema}.checkpoints (run_id, payload)
                    VALUES (%s, %s::jsonb)
                    ON CONFLICT (run_id)
                    DO UPDATE SET payload = EXCLUDED.payload, updated_at = now()
                    """,
                    (run_id, payload_json),
                )

    def load_checkpoint(self, run_id: str) -> dict | None:
        if self._use_fallback:
            return self._checkpoints.get(run_id)

        psycopg, dict_row = _import_psycopg()

        with psycopg.connect(self._dsn, autocommit=True, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"SELECT payload FROM {self._schema}.checkpoints WHERE run_id = %s",
                    (run_id,),
                )
                row = cur.fetchone()

        if row is None:
            return None

        payload = row["payload"]
        if isinstance(payload, str):
            return json.loads(payload)
        return payload


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