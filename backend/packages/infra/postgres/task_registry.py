from __future__ import annotations

import json
from datetime import datetime, timezone

from application.errors import TaskNotFoundError
from application.task_service import TaskRecord, TaskRegistry
from infra.postgres.config import PostgresSettings, validate_identifier


class PostgresTaskRegistry(TaskRegistry):
    """Реестр задач поверх PostgreSQL с in-memory fallback для dev/test."""

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
        self._tasks: dict[str, TaskRecord] = {}

        if not self._use_fallback and not self._dsn:
            raise ValueError("DSN обязателен для PostgreSQL task registry")

    @classmethod
    def from_settings(
        cls,
        settings: PostgresSettings,
        *,
        use_fallback_if_unset: bool = True,
    ) -> "PostgresTaskRegistry":
        return cls(dsn=settings.dsn, schema=settings.schema, use_fallback_if_unset=use_fallback_if_unset)

    def save(self, record: TaskRecord) -> None:
        if self._use_fallback:
            now_utc = datetime.now(timezone.utc)
            current = self._tasks.get(record.task_id)

            if current is None:
                created_at = record.created_at or now_utc
                updated_at = record.updated_at or now_utc
            else:
                created_at = current.created_at or record.created_at or now_utc
                updated_at = now_utc

            self._tasks[record.task_id] = record.model_copy(update={"created_at": created_at, "updated_at": updated_at})
            return

        psycopg, dict_row = _import_psycopg()
        now_utc = datetime.now(timezone.utc)
        created_at = record.created_at or now_utc
        details_json = json.dumps(record.details, ensure_ascii=False)

        with psycopg.connect(self._dsn, autocommit=True, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    INSERT INTO {self._schema}.tasks (
                        task_id,
                        task_type,
                        status,
                        current_node,
                        details,
                        created_at,
                        updated_at
                    )
                    VALUES (%s, %s, %s, %s, %s::jsonb, %s, now())
                    ON CONFLICT (task_id)
                    DO UPDATE SET
                        task_type = EXCLUDED.task_type,
                        status = EXCLUDED.status,
                        current_node = EXCLUDED.current_node,
                        details = EXCLUDED.details,
                        updated_at = now()
                    """,
                    (
                        record.task_id,
                        record.task_type,
                        record.status,
                        record.current_node,
                        details_json,
                        created_at,
                    ),
                )

    def get(self, task_id: str) -> TaskRecord:
        if self._use_fallback:
            item = self._tasks.get(task_id)
            if item is None:
                raise TaskNotFoundError(f"Задача {task_id} не найдена")
            return item

        psycopg, dict_row = _import_psycopg()

        with psycopg.connect(self._dsn, autocommit=True, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    SELECT task_id, task_type, status, current_node, details, created_at, updated_at
                    FROM {self._schema}.tasks
                    WHERE task_id = %s
                    """,
                    (task_id,),
                )
                row = cur.fetchone()

        if row is None:
            raise TaskNotFoundError(f"Задача {task_id} не найдена")

        return _row_to_task_record(row)

    def list_tasks(self, limit: int = 50, offset: int = 0) -> list[TaskRecord]:
        if self._use_fallback:
            ordered = sorted(
                self._tasks.values(),
                key=lambda item: item.updated_at or item.created_at or datetime.min.replace(tzinfo=timezone.utc),
                reverse=True,
            )
            return ordered[offset : offset + limit]

        psycopg, dict_row = _import_psycopg()

        with psycopg.connect(self._dsn, autocommit=True, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    SELECT task_id, task_type, status, current_node, details, created_at, updated_at
                    FROM {self._schema}.tasks
                    ORDER BY updated_at DESC
                    LIMIT %s OFFSET %s
                    """,
                    (limit, offset),
                )
                rows = cur.fetchall()

        return [_row_to_task_record(row) for row in rows]


def _row_to_task_record(row: dict) -> TaskRecord:
    details = row.get("details") or {}
    if isinstance(details, str):
        details = json.loads(details)

    return TaskRecord(
        task_id=row["task_id"],
        task_type=row["task_type"],
        status=row["status"],
        current_node=row.get("current_node"),
        details=details,
        created_at=row.get("created_at"),
        updated_at=row.get("updated_at"),
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
