from __future__ import annotations

import json
from datetime import datetime, timezone

from application.hitl_action_store import (
    HitlActionListPage,
    HitlActionRecord,
    HitlActionStore,
    HitlActionSummary,
    _build_hitl_action_summary,
    _filter_actions,
    build_hitl_action_cursor,
    decode_hitl_action_cursor,
)
from application.errors import TaskNotFoundError
from infra.postgres.config import PostgresSettings, validate_identifier


class PostgresHitlActionStore(HitlActionStore):
    """PostgreSQL хранилище reviewer действий HITL с in-memory fallback."""

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
        self._actions: dict[str, HitlActionRecord] = {}

        if not self._use_fallback and not self._dsn:
            raise ValueError("DSN обязателен для PostgreSQL HITL action store")

    @classmethod
    def from_settings(
        cls,
        settings: PostgresSettings,
        *,
        use_fallback_if_unset: bool | None = None,
    ) -> "PostgresHitlActionStore":
        fallback_enabled = settings.allow_fallback_persistence if use_fallback_if_unset is None else use_fallback_if_unset
        return cls(dsn=settings.dsn, schema=settings.schema, use_fallback_if_unset=fallback_enabled)

    def save_action(self, record: HitlActionRecord) -> None:
        if self._use_fallback:
            current = self._actions.get(record.action_id)
            created_at = current.created_at if current else record.created_at
            self._actions[record.action_id] = record.model_copy(update={"created_at": created_at})
            return

        psycopg, dict_row = _import_psycopg()
        metadata_json = json.dumps(record.metadata, ensure_ascii=False)

        with psycopg.connect(self._dsn, autocommit=True, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    INSERT INTO {self._schema}.hitl_actions (
                        action_id,
                        task_id,
                        iteration,
                        decision,
                        status,
                        comment,
                        reviewer,
                        idempotency_key,
                        metadata,
                        created_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, COALESCE(%s, now()))
                    ON CONFLICT (action_id)
                    DO UPDATE SET
                        task_id = EXCLUDED.task_id,
                        iteration = EXCLUDED.iteration,
                        decision = EXCLUDED.decision,
                        status = EXCLUDED.status,
                        comment = EXCLUDED.comment,
                        reviewer = EXCLUDED.reviewer,
                        idempotency_key = EXCLUDED.idempotency_key,
                        metadata = EXCLUDED.metadata,
                        updated_at = now()
                    """,
                    (
                        record.action_id,
                        record.task_id,
                        record.iteration,
                        record.decision,
                        record.status,
                        record.comment,
                        record.reviewer,
                        record.idempotency_key,
                        metadata_json,
                        record.created_at,
                    ),
                )

    def get_action(self, action_id: str) -> HitlActionRecord:
        if self._use_fallback:
            action = self._actions.get(action_id)
            if action is None:
                raise TaskNotFoundError(f"HITL action {action_id} не найден")
            return action

        psycopg, dict_row = _import_psycopg()
        with psycopg.connect(self._dsn, autocommit=True, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    SELECT action_id, task_id, iteration, decision, status, comment, reviewer, idempotency_key, metadata, created_at, updated_at
                    FROM {self._schema}.hitl_actions
                    WHERE action_id = %s
                    """,
                    (action_id,),
                )
                row = cur.fetchone()

        if row is None:
            raise TaskNotFoundError(f"HITL action {action_id} не найден")
        return _row_to_hitl_action_record(row)

    def list_actions(
        self,
        *,
        limit: int = 50,
        cursor: str | None = None,
        task_id: str | None = None,
        decision: str | None = None,
        status: str | None = None,
        reviewer: str | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
    ) -> HitlActionListPage:
        if self._use_fallback:
            return self._list_actions_fallback(
                limit=limit,
                cursor=cursor,
                task_id=task_id,
                decision=decision,
                status=status,
                reviewer=reviewer,
                created_from=created_from,
                created_to=created_to,
            )

        cursor_payload = decode_hitl_action_cursor(cursor) if cursor else None
        normalized_from = _to_utc(created_from) if created_from else None
        normalized_to = _to_utc(created_to) if created_to else None

        where_clauses = ["1=1"]
        params: list[object] = []
        if task_id:
            where_clauses.append("task_id = %s")
            params.append(task_id)
        if decision:
            where_clauses.append("decision = %s")
            params.append(decision)
        if status:
            where_clauses.append("status = %s")
            params.append(status)
        if reviewer:
            where_clauses.append("reviewer = %s")
            params.append(reviewer)
        if normalized_from:
            where_clauses.append("created_at >= %s")
            params.append(normalized_from)
        if normalized_to:
            where_clauses.append("created_at <= %s")
            params.append(normalized_to)
        if cursor_payload:
            where_clauses.append("(created_at < %s OR (created_at = %s AND action_id < %s))")
            params.extend([cursor_payload.created_at, cursor_payload.created_at, cursor_payload.action_id])

        query = f"""
            SELECT action_id, task_id, iteration, decision, status, comment, reviewer, idempotency_key, metadata, created_at, updated_at
            FROM {self._schema}.hitl_actions
            WHERE {" AND ".join(where_clauses)}
            ORDER BY created_at DESC, action_id DESC
            LIMIT %s
        """
        params.append(limit + 1)

        psycopg, dict_row = _import_psycopg()
        with psycopg.connect(self._dsn, autocommit=True, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute(query, tuple(params))
                rows = cur.fetchall()

        records = [_row_to_hitl_action_record(row) for row in rows]
        has_more = len(records) > limit
        items = records[:limit]
        next_cursor = build_hitl_action_cursor(items[-1]) if has_more and items else None
        return HitlActionListPage(
            items=items,
            limit=limit,
            total_returned=len(items),
            next_cursor=next_cursor,
            has_more=has_more,
        )

    def summarize_actions(
        self,
        *,
        task_id: str | None = None,
        decision: str | None = None,
        status: str | None = None,
        reviewer: str | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
    ) -> HitlActionSummary:
        if self._use_fallback:
            filtered = _filter_actions(
                self._actions.values(),
                task_id=task_id,
                decision=decision,
                status=status,
                reviewer=reviewer,
                created_from=created_from,
                created_to=created_to,
            )
            return _build_hitl_action_summary(filtered)

        normalized_from = _to_utc(created_from) if created_from else None
        normalized_to = _to_utc(created_to) if created_to else None

        where_clauses = ["1=1"]
        params: list[object] = []
        if task_id:
            where_clauses.append("task_id = %s")
            params.append(task_id)
        if decision:
            where_clauses.append("decision = %s")
            params.append(decision)
        if status:
            where_clauses.append("status = %s")
            params.append(status)
        if reviewer:
            where_clauses.append("reviewer = %s")
            params.append(reviewer)
        if normalized_from:
            where_clauses.append("created_at >= %s")
            params.append(normalized_from)
        if normalized_to:
            where_clauses.append("created_at <= %s")
            params.append(normalized_to)

        query = f"""
            SELECT action_id, task_id, iteration, decision, status, comment, reviewer, idempotency_key, metadata, created_at, updated_at
            FROM {self._schema}.hitl_actions
            WHERE {" AND ".join(where_clauses)}
        """

        psycopg, dict_row = _import_psycopg()
        with psycopg.connect(self._dsn, autocommit=True, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute(query, tuple(params))
                rows = cur.fetchall()

        return _build_hitl_action_summary([_row_to_hitl_action_record(row) for row in rows])

    def _list_actions_fallback(
        self,
        *,
        limit: int,
        cursor: str | None,
        task_id: str | None,
        decision: str | None,
        status: str | None,
        reviewer: str | None,
        created_from: datetime | None,
        created_to: datetime | None,
    ) -> HitlActionListPage:
        cursor_payload = decode_hitl_action_cursor(cursor) if cursor else None
        filtered = _filter_actions(
            self._actions.values(),
            task_id=task_id,
            decision=decision,
            status=status,
            reviewer=reviewer,
            created_from=created_from,
            created_to=created_to,
        )

        if cursor_payload:
            filtered = [
                item
                for item in filtered
                if _to_utc(item.created_at or item.updated_at or datetime.min.replace(tzinfo=timezone.utc))
                < cursor_payload.created_at
                or (
                    _to_utc(item.created_at or item.updated_at or datetime.min.replace(tzinfo=timezone.utc))
                    == cursor_payload.created_at
                    and item.action_id < cursor_payload.action_id
                )
            ]

        ordered = sorted(
            filtered,
            key=lambda action: (_to_utc(action.created_at or datetime.min.replace(tzinfo=timezone.utc)), action.action_id),
            reverse=True,
        )
        window = ordered[: limit + 1]
        has_more = len(window) > limit
        items = window[:limit]
        next_cursor = build_hitl_action_cursor(items[-1]) if has_more and items else None
        return HitlActionListPage(
            items=items,
            limit=limit,
            total_returned=len(items),
            next_cursor=next_cursor,
            has_more=has_more,
        )


def _row_to_hitl_action_record(row: dict) -> HitlActionRecord:
    metadata_payload = row["metadata"]
    if isinstance(metadata_payload, str):
        metadata_payload = json.loads(metadata_payload)
    return HitlActionRecord(
        action_id=row["action_id"],
        task_id=row["task_id"],
        iteration=row["iteration"],
        decision=row["decision"],
        status=row["status"],
        comment=row["comment"],
        reviewer=row["reviewer"],
        idempotency_key=row["idempotency_key"],
        metadata=metadata_payload or {},
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


def _to_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
