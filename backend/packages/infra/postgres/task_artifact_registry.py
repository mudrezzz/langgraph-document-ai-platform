from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from application.errors import TaskArtifactLinkNotFoundError
from infra.postgres.config import PostgresSettings, validate_identifier
from pydantic import BaseModel, Field


class _TaskArtifactLinkRecord(BaseModel):
    """Внутренняя модель связи task -> artifact в PostgreSQL адаптере."""

    task_id: str
    artifact_id: str
    retrieval_task_id: str
    traceability: dict = Field(default_factory=dict)
    created_at: datetime | None = None
    updated_at: datetime | None = None


class PostgresTaskArtifactRegistry:
    """Реестр связей authoring task -> artifact поверх PostgreSQL."""

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
        self._links: dict[str, _TaskArtifactLinkRecord] = {}

        if not self._use_fallback and not self._dsn:
            raise ValueError("DSN обязателен для PostgreSQL task artifact registry")

    @classmethod
    def from_settings(
        cls,
        settings: PostgresSettings,
        *,
        use_fallback_if_unset: bool | None = None,
    ) -> "PostgresTaskArtifactRegistry":
        fallback_enabled = settings.allow_fallback_persistence if use_fallback_if_unset is None else use_fallback_if_unset
        return cls(dsn=settings.dsn, schema=settings.schema, use_fallback_if_unset=fallback_enabled)

    def save_link(
        self,
        *,
        task_id: str,
        artifact_id: str,
        retrieval_task_id: str,
        traceability: dict,
    ) -> None:
        if self._use_fallback:
            now_utc = datetime.now(timezone.utc)
            current = self._links.get(task_id)
            self._links[task_id] = _TaskArtifactLinkRecord(
                task_id=task_id,
                artifact_id=artifact_id,
                retrieval_task_id=retrieval_task_id,
                traceability=dict(traceability),
                created_at=current.created_at if current else now_utc,
                updated_at=now_utc,
            )
            return

        psycopg, dict_row = _import_psycopg()
        traceability_json = json.dumps(traceability, ensure_ascii=False)

        with psycopg.connect(self._dsn, autocommit=True, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    INSERT INTO {self._schema}.task_artifacts (
                        task_id,
                        artifact_id,
                        retrieval_task_id,
                        traceability
                    )
                    VALUES (%s, %s, %s, %s::jsonb)
                    ON CONFLICT (task_id)
                    DO UPDATE SET
                        artifact_id = EXCLUDED.artifact_id,
                        retrieval_task_id = EXCLUDED.retrieval_task_id,
                        traceability = EXCLUDED.traceability,
                        updated_at = now()
                    """,
                    (task_id, artifact_id, retrieval_task_id, traceability_json),
                )

    def get_link(self, task_id: str) -> _TaskArtifactLinkRecord:
        if self._use_fallback:
            link = self._links.get(task_id)
            if link is None:
                raise TaskArtifactLinkNotFoundError(f"Связь task->artifact для {task_id} не найдена")
            return link

        psycopg, dict_row = _import_psycopg()
        with psycopg.connect(self._dsn, autocommit=True, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    SELECT task_id, artifact_id, retrieval_task_id, traceability, created_at, updated_at
                    FROM {self._schema}.task_artifacts
                    WHERE task_id = %s
                    """,
                    (task_id,),
                )
                row = cur.fetchone()

        if row is None:
            raise TaskArtifactLinkNotFoundError(f"Связь task->artifact для {task_id} не найдена")

        traceability_payload = row["traceability"]
        if isinstance(traceability_payload, str):
            traceability_payload = json.loads(traceability_payload)

        return _TaskArtifactLinkRecord(
            task_id=row["task_id"],
            artifact_id=row["artifact_id"],
            retrieval_task_id=row["retrieval_task_id"],
            traceability=traceability_payload or {},
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )


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
