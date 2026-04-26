from __future__ import annotations

import json
from datetime import datetime, timezone

from application.errors import TaskNotFoundError
from application.task_service import (
    TaskEventListPage,
    TaskEventRecord,
    TaskEventSummary,
    TaskEventTransitionStat,
    TaskListPage,
    TaskObservabilitySummary,
    TaskRecord,
    TaskRegistry,
    _build_task_observability_summary,
    _filter_tasks_for_summary,
    build_task_cursor,
    build_task_event_cursor,
    decode_task_cursor,
    decode_task_event_cursor,
)
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
        self._events: list[TaskEventRecord] = []

        if not self._use_fallback and not self._dsn:
            raise ValueError("DSN обязателен для PostgreSQL task registry")

    @classmethod
    def from_settings(
        cls,
        settings: PostgresSettings,
        *,
        use_fallback_if_unset: bool | None = None,
    ) -> "PostgresTaskRegistry":
        fallback_enabled = settings.allow_fallback_persistence if use_fallback_if_unset is None else use_fallback_if_unset
        return cls(dsn=settings.dsn, schema=settings.schema, use_fallback_if_unset=fallback_enabled)

    def save(self, record: TaskRecord) -> None:
        if self._use_fallback:
            self._save_with_fallback(record)
            return

        psycopg, dict_row = _import_psycopg()
        now_utc = datetime.now(timezone.utc)
        created_at = record.created_at or now_utc
        details_json = json.dumps(record.details, ensure_ascii=False)

        with psycopg.connect(self._dsn, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    SELECT task_type, status, current_node
                    FROM {self._schema}.tasks
                    WHERE task_id = %s
                    FOR UPDATE
                    """,
                    (record.task_id,),
                )
                previous = cur.fetchone()

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

                # Пишем audit trail только для создания задачи или смены статуса.
                previous_status = previous.get("status") if previous else None
                if previous is None or previous_status != record.status:
                    previous_node = previous.get("current_node") if previous else None
                    event_payload = json.dumps({"details": record.details}, ensure_ascii=False)
                    cur.execute(
                        f"""
                        INSERT INTO {self._schema}.task_events (
                            task_id,
                            task_type,
                            from_status,
                            to_status,
                            from_current_node,
                            to_current_node,
                            event_payload
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb)
                        """,
                        (
                            record.task_id,
                            record.task_type,
                            previous_status,
                            record.status,
                            previous_node,
                            record.current_node,
                            event_payload,
                        ),
                    )

            conn.commit()

    def record_event(self, record: TaskEventRecord) -> None:
        if self._use_fallback:
            self._record_event_with_fallback(record)
            return

        psycopg, _ = _import_psycopg()
        event_payload = json.dumps(record.event_payload, ensure_ascii=False)
        with psycopg.connect(self._dsn) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    INSERT INTO {self._schema}.task_events (
                        task_id,
                        task_type,
                        from_status,
                        to_status,
                        from_current_node,
                        to_current_node,
                        event_payload
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb)
                    """,
                    (
                        record.task_id,
                        record.task_type,
                        record.from_status,
                        record.to_status,
                        record.from_current_node,
                        record.to_current_node,
                        event_payload,
                    ),
                )
            conn.commit()

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

    def list_tasks(
        self,
        *,
        limit: int = 50,
        cursor: str | None = None,
        status: str | None = None,
        task_type: str | None = None,
        updated_from: datetime | None = None,
        updated_to: datetime | None = None,
    ) -> TaskListPage:
        if self._use_fallback:
            return self._list_tasks_fallback(
                limit=limit,
                cursor=cursor,
                status=status,
                task_type=task_type,
                updated_from=updated_from,
                updated_to=updated_to,
            )

        cursor_payload = decode_task_cursor(cursor) if cursor else None
        normalized_from = _normalize_datetime(updated_from) if updated_from else None
        normalized_to = _normalize_datetime(updated_to) if updated_to else None

        where_clauses = ["1=1"]
        params: list[object] = []

        if status:
            where_clauses.append("status = %s")
            params.append(status)
        if task_type:
            where_clauses.append("task_type = %s")
            params.append(task_type)
        if normalized_from:
            where_clauses.append("updated_at >= %s")
            params.append(normalized_from)
        if normalized_to:
            where_clauses.append("updated_at <= %s")
            params.append(normalized_to)
        if cursor_payload:
            where_clauses.append("(updated_at < %s OR (updated_at = %s AND task_id < %s))")
            params.extend([cursor_payload.updated_at, cursor_payload.updated_at, cursor_payload.task_id])

        query = f"""
            SELECT task_id, task_type, status, current_node, details, created_at, updated_at
            FROM {self._schema}.tasks
            WHERE {" AND ".join(where_clauses)}
            ORDER BY updated_at DESC, task_id DESC
            LIMIT %s
        """
        params.append(limit + 1)

        psycopg, dict_row = _import_psycopg()
        with psycopg.connect(self._dsn, autocommit=True, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute(query, tuple(params))
                rows = cur.fetchall()

        records = [_row_to_task_record(row) for row in rows]
        has_more = len(records) > limit
        items = records[:limit]
        next_cursor = build_task_cursor(items[-1]) if has_more and items else None

        return TaskListPage(
            items=items,
            limit=limit,
            total_returned=len(items),
            next_cursor=next_cursor,
            has_more=has_more,
        )

    def list_task_events(
        self,
        *,
        limit: int = 100,
        cursor: str | None = None,
        task_id: str | None = None,
        task_type: str | None = None,
        from_status: str | None = None,
        to_status: str | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
    ) -> TaskEventListPage:
        if self._use_fallback:
            return self._list_task_events_fallback(
                limit=limit,
                cursor=cursor,
                task_id=task_id,
                task_type=task_type,
                from_status=from_status,
                to_status=to_status,
                created_from=created_from,
                created_to=created_to,
            )

        cursor_payload = decode_task_event_cursor(cursor) if cursor else None
        normalized_from = _normalize_datetime(created_from) if created_from else None
        normalized_to = _normalize_datetime(created_to) if created_to else None

        where_clauses = ["1=1"]
        params: list[object] = []

        if task_id:
            where_clauses.append("task_id = %s")
            params.append(task_id)
        if task_type:
            where_clauses.append("task_type = %s")
            params.append(task_type)
        if from_status is not None:
            where_clauses.append("from_status = %s")
            params.append(from_status)
        if to_status:
            where_clauses.append("to_status = %s")
            params.append(to_status)
        if normalized_from:
            where_clauses.append("created_at >= %s")
            params.append(normalized_from)
        if normalized_to:
            where_clauses.append("created_at <= %s")
            params.append(normalized_to)
        if cursor_payload:
            where_clauses.append("(created_at < %s OR (created_at = %s AND event_id < %s))")
            params.extend([cursor_payload.created_at, cursor_payload.created_at, cursor_payload.event_id])

        query = f"""
            SELECT
                event_id,
                task_id,
                task_type,
                from_status,
                to_status,
                from_current_node,
                to_current_node,
                event_payload,
                created_at
            FROM {self._schema}.task_events
            WHERE {" AND ".join(where_clauses)}
            ORDER BY created_at DESC, event_id DESC
            LIMIT %s
        """
        params.append(limit + 1)

        psycopg, dict_row = _import_psycopg()
        with psycopg.connect(self._dsn, autocommit=True, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute(query, tuple(params))
                rows = cur.fetchall()

        events = [_row_to_task_event(row) for row in rows]
        has_more = len(events) > limit
        items = events[:limit]
        next_cursor = build_task_event_cursor(items[-1]) if has_more and items else None

        return TaskEventListPage(
            items=items,
            limit=limit,
            total_returned=len(items),
            next_cursor=next_cursor,
            has_more=has_more,
        )

    def summarize_task_events(
        self,
        *,
        task_id: str | None = None,
        task_type: str | None = None,
        from_status: str | None = None,
        to_status: str | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
    ) -> TaskEventSummary:
        if self._use_fallback:
            return self._summarize_task_events_fallback(
                task_id=task_id,
                task_type=task_type,
                from_status=from_status,
                to_status=to_status,
                created_from=created_from,
                created_to=created_to,
            )

        normalized_from = _normalize_datetime(created_from) if created_from else None
        normalized_to = _normalize_datetime(created_to) if created_to else None

        where_clauses = ["1=1"]
        params: list[object] = []

        if task_id:
            where_clauses.append("task_id = %s")
            params.append(task_id)
        if task_type:
            where_clauses.append("task_type = %s")
            params.append(task_type)
        if from_status is not None:
            where_clauses.append("from_status = %s")
            params.append(from_status)
        if to_status:
            where_clauses.append("to_status = %s")
            params.append(to_status)
        if normalized_from:
            where_clauses.append("created_at >= %s")
            params.append(normalized_from)
        if normalized_to:
            where_clauses.append("created_at <= %s")
            params.append(normalized_to)

        where_clause = " AND ".join(where_clauses)
        psycopg, dict_row = _import_psycopg()
        with psycopg.connect(self._dsn, autocommit=True, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    SELECT from_status, to_status, COUNT(*) AS total
                    FROM {self._schema}.task_events
                    WHERE {where_clause}
                    GROUP BY from_status, to_status
                    ORDER BY total DESC, to_status ASC, from_status ASC
                    """,
                    tuple(params),
                )
                rows = cur.fetchall()

                cur.execute(
                    f"""
                    SELECT
                        COUNT(*) AS total_events,
                        COUNT(DISTINCT task_id) AS unique_tasks
                    FROM {self._schema}.task_events
                    WHERE {where_clause}
                    """,
                    tuple(params),
                )
                totals_row = cur.fetchone() or {}

        transitions = [
            TaskEventTransitionStat(
                from_status=row.get("from_status"),
                to_status=row["to_status"],
                total=int(row["total"]),
            )
            for row in rows
        ]
        return TaskEventSummary(
            total_events=int(totals_row.get("total_events", 0) or 0),
            unique_tasks=int(totals_row.get("unique_tasks", 0) or 0),
            transitions=transitions,
        )

    def summarize_tasks(
        self,
        *,
        status: str | None = None,
        task_type: str | None = None,
        updated_from: datetime | None = None,
        updated_to: datetime | None = None,
    ) -> TaskObservabilitySummary:
        if self._use_fallback:
            filtered = _filter_tasks_for_summary(
                self._tasks.values(),
                status=status,
                task_type=task_type,
                updated_from=updated_from,
                updated_to=updated_to,
            )
            return _build_task_observability_summary(filtered)

        normalized_from = _normalize_datetime(updated_from) if updated_from else None
        normalized_to = _normalize_datetime(updated_to) if updated_to else None

        where_clauses = ["1=1"]
        params: list[object] = []

        if status:
            where_clauses.append("status = %s")
            params.append(status)
        if task_type:
            where_clauses.append("task_type = %s")
            params.append(task_type)
        if normalized_from:
            where_clauses.append("updated_at >= %s")
            params.append(normalized_from)
        if normalized_to:
            where_clauses.append("updated_at <= %s")
            params.append(normalized_to)

        query = f"""
            SELECT task_id, task_type, status, current_node, details, created_at, updated_at
            FROM {self._schema}.tasks
            WHERE {" AND ".join(where_clauses)}
        """

        psycopg, dict_row = _import_psycopg()
        with psycopg.connect(self._dsn, autocommit=True, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute(query, tuple(params))
                rows = cur.fetchall()

        return _build_task_observability_summary([_row_to_task_record(row) for row in rows])

    def _save_with_fallback(self, record: TaskRecord) -> None:
        now_utc = datetime.now(timezone.utc)
        previous = self._tasks.get(record.task_id)

        if previous is None:
            created_at = record.created_at or now_utc
            updated_at = record.updated_at or now_utc
        else:
            created_at = previous.created_at or record.created_at or now_utc
            updated_at = now_utc

        saved_record = record.model_copy(update={"created_at": created_at, "updated_at": updated_at})
        self._tasks[record.task_id] = saved_record

        if previous is not None and previous.status == saved_record.status:
            return

        event = TaskEventRecord(
            event_id=len(self._events) + 1,
            task_id=saved_record.task_id,
            task_type=saved_record.task_type,
            from_status=previous.status if previous else None,
            to_status=saved_record.status,
            from_current_node=previous.current_node if previous else None,
            to_current_node=saved_record.current_node,
            event_payload={"details": saved_record.details},
            created_at=saved_record.updated_at or now_utc,
        )
        self._events.append(event)

    def _record_event_with_fallback(self, record: TaskEventRecord) -> None:
        event = record.model_copy(
            update={
                "event_id": record.event_id or len(self._events) + 1,
                "created_at": record.created_at or datetime.now(timezone.utc),
            }
        )
        self._events.append(event)

    def _list_tasks_fallback(
        self,
        *,
        limit: int = 50,
        cursor: str | None = None,
        status: str | None = None,
        task_type: str | None = None,
        updated_from: datetime | None = None,
        updated_to: datetime | None = None,
    ) -> TaskListPage:
        cursor_payload = decode_task_cursor(cursor) if cursor else None
        normalized_from = _normalize_datetime(updated_from) if updated_from else None
        normalized_to = _normalize_datetime(updated_to) if updated_to else None

        filtered: list[TaskRecord] = []
        for item in self._tasks.values():
            if status and item.status != status:
                continue
            if task_type and item.task_type != task_type:
                continue

            item_updated_at = _effective_task_timestamp(item)
            if normalized_from and item_updated_at < normalized_from:
                continue
            if normalized_to and item_updated_at > normalized_to:
                continue
            if cursor_payload and not _is_before_task_cursor(item, cursor_payload.updated_at, cursor_payload.task_id):
                continue
            filtered.append(item)

        ordered = sorted(filtered, key=lambda item: (_effective_task_timestamp(item), item.task_id), reverse=True)
        window = ordered[: limit + 1]
        has_more = len(window) > limit
        items = window[:limit]
        next_cursor = build_task_cursor(items[-1]) if has_more and items else None

        return TaskListPage(
            items=items,
            limit=limit,
            total_returned=len(items),
            next_cursor=next_cursor,
            has_more=has_more,
        )

    def _list_task_events_fallback(
        self,
        *,
        limit: int = 100,
        cursor: str | None = None,
        task_id: str | None = None,
        task_type: str | None = None,
        from_status: str | None = None,
        to_status: str | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
    ) -> TaskEventListPage:
        cursor_payload = decode_task_event_cursor(cursor) if cursor else None
        normalized_from = _normalize_datetime(created_from) if created_from else None
        normalized_to = _normalize_datetime(created_to) if created_to else None

        filtered: list[TaskEventRecord] = []
        for item in self._events:
            if task_id and item.task_id != task_id:
                continue
            if task_type and item.task_type != task_type:
                continue
            if from_status is not None and item.from_status != from_status:
                continue
            if to_status and item.to_status != to_status:
                continue

            item_created_at = _effective_event_timestamp(item)
            if normalized_from and item_created_at < normalized_from:
                continue
            if normalized_to and item_created_at > normalized_to:
                continue
            if cursor_payload and not _is_before_event_cursor(item, cursor_payload.created_at, cursor_payload.event_id):
                continue
            filtered.append(item)

        ordered = sorted(filtered, key=lambda item: (_effective_event_timestamp(item), item.event_id or 0), reverse=True)
        window = ordered[: limit + 1]
        has_more = len(window) > limit
        items = window[:limit]
        next_cursor = build_task_event_cursor(items[-1]) if has_more and items else None

        return TaskEventListPage(
            items=items,
            limit=limit,
            total_returned=len(items),
            next_cursor=next_cursor,
            has_more=has_more,
        )

    def _summarize_task_events_fallback(
        self,
        *,
        task_id: str | None = None,
        task_type: str | None = None,
        from_status: str | None = None,
        to_status: str | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
    ) -> TaskEventSummary:
        normalized_from = _normalize_datetime(created_from) if created_from else None
        normalized_to = _normalize_datetime(created_to) if created_to else None

        filtered: list[TaskEventRecord] = []
        for item in self._events:
            if task_id and item.task_id != task_id:
                continue
            if task_type and item.task_type != task_type:
                continue
            if from_status is not None and item.from_status != from_status:
                continue
            if to_status and item.to_status != to_status:
                continue

            item_created_at = _effective_event_timestamp(item)
            if normalized_from and item_created_at < normalized_from:
                continue
            if normalized_to and item_created_at > normalized_to:
                continue
            filtered.append(item)

        buckets: dict[tuple[str | None, str], int] = {}
        for item in filtered:
            key = (item.from_status, item.to_status)
            buckets[key] = buckets.get(key, 0) + 1

        transitions = [
            TaskEventTransitionStat(from_status=from_status_key, to_status=to_status_key, total=total)
            for (from_status_key, to_status_key), total in buckets.items()
        ]
        transitions.sort(key=lambda item: (-item.total, item.to_status, item.from_status or ""))

        return TaskEventSummary(
            total_events=len(filtered),
            unique_tasks=len({item.task_id for item in filtered}),
            transitions=transitions,
        )


def _effective_task_timestamp(task: TaskRecord) -> datetime:
    return _normalize_datetime(task.updated_at or task.created_at or datetime.min.replace(tzinfo=timezone.utc))


def _effective_event_timestamp(event: TaskEventRecord) -> datetime:
    return _normalize_datetime(event.created_at or datetime.min.replace(tzinfo=timezone.utc))


def _normalize_datetime(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _is_before_task_cursor(task: TaskRecord, cursor_time: datetime, cursor_task_id: str) -> bool:
    task_time = _effective_task_timestamp(task)
    if task_time < cursor_time:
        return True
    if task_time > cursor_time:
        return False
    return task.task_id < cursor_task_id


def _is_before_event_cursor(event: TaskEventRecord, cursor_time: datetime, cursor_event_id: int) -> bool:
    event_time = _effective_event_timestamp(event)
    if event_time < cursor_time:
        return True
    if event_time > cursor_time:
        return False
    return (event.event_id or 0) < cursor_event_id


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


def _row_to_task_event(row: dict) -> TaskEventRecord:
    payload = row.get("event_payload") or {}
    if isinstance(payload, str):
        payload = json.loads(payload)

    return TaskEventRecord(
        event_id=int(row["event_id"]) if row.get("event_id") is not None else None,
        task_id=row["task_id"],
        task_type=row["task_type"],
        from_status=row.get("from_status"),
        to_status=row["to_status"],
        from_current_node=row.get("from_current_node"),
        to_current_node=row.get("to_current_node"),
        event_payload=payload,
        created_at=row.get("created_at"),
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
