from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from application.template_library_service import TemplateRecord
from infra.postgres.config import PostgresSettings, validate_identifier
from schemas.documents.contracts import TemplateSpec


class PostgresTemplateStore:
    """Template library store backed by PostgreSQL with in-memory fallback."""

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
        self._templates: dict[tuple[str, str], TemplateRecord] = {}

        if not self._use_fallback and not self._dsn:
            raise ValueError("DSN обязателен для PostgreSQL template store")

    @classmethod
    def from_settings(
        cls,
        settings: PostgresSettings,
        *,
        use_fallback_if_unset: bool | None = None,
    ) -> "PostgresTemplateStore":
        fallback_enabled = settings.allow_fallback_persistence if use_fallback_if_unset is None else use_fallback_if_unset
        return cls(dsn=settings.dsn, schema=settings.schema, use_fallback_if_unset=fallback_enabled)

    def upsert_template(self, template_spec: TemplateSpec, *, metadata: dict | None = None) -> str:
        if self._use_fallback:
            now_utc = datetime.now(timezone.utc)
            key = (template_spec.template_id, template_spec.version)
            current = self._templates.get(key)
            self._templates[key] = TemplateRecord(
                template_id=template_spec.template_id,
                version=template_spec.version,
                template_spec=template_spec,
                metadata=dict(metadata or {}),
                created_at=current.created_at if current is not None else now_utc,
                updated_at=now_utc,
            )
            return template_spec.template_id

        psycopg, dict_row = _import_psycopg()
        payload = template_spec.model_dump(mode="json")

        with psycopg.connect(self._dsn, autocommit=True, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    INSERT INTO {self._schema}.document_templates (
                        template_id,
                        version,
                        metadata,
                        payload
                    )
                    VALUES (%s, %s, %s::jsonb, %s::jsonb)
                    ON CONFLICT (template_id, version)
                    DO UPDATE SET
                        metadata = EXCLUDED.metadata,
                        payload = EXCLUDED.payload,
                        updated_at = now()
                    """,
                    (
                        template_spec.template_id,
                        template_spec.version,
                        json.dumps(dict(metadata or {}), ensure_ascii=False),
                        json.dumps(payload, ensure_ascii=False),
                    ),
                )
        return template_spec.template_id

    def get_template(self, template_id: str, version: str | None = None) -> TemplateRecord:
        if self._use_fallback:
            if version is not None:
                item = self._templates.get((template_id, version))
                if item is None:
                    raise KeyError(f"Template {template_id}:{version} не найден")
                return item

            candidates = [item for key, item in self._templates.items() if key[0] == template_id]
            if not candidates:
                raise KeyError(f"Template {template_id} не найден")
            return sorted(
                candidates,
                key=lambda item: (item.updated_at or datetime.min.replace(tzinfo=timezone.utc), item.version),
                reverse=True,
            )[0]

        psycopg, dict_row = _import_psycopg()
        query = (
            f"""
            SELECT template_id, version, metadata, payload, created_at, updated_at
            FROM {self._schema}.document_templates
            WHERE template_id = %s AND version = %s
            """
            if version is not None
            else f"""
            SELECT template_id, version, metadata, payload, created_at, updated_at
            FROM {self._schema}.document_templates
            WHERE template_id = %s
            ORDER BY updated_at DESC, version DESC
            LIMIT 1
            """
        )
        params = (template_id, version) if version is not None else (template_id,)

        with psycopg.connect(self._dsn, autocommit=True, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
                row = cur.fetchone()

        if row is None:
            raise KeyError(f"Template {template_id}:{version or 'latest'} не найден")
        return _row_to_template_record(row)

    def list_templates(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
        template_id: str | None = None,
    ) -> list[TemplateRecord]:
        _validate_page(limit=limit, offset=offset)

        if self._use_fallback:
            ordered = sorted(
                self._templates.values(),
                key=lambda item: (item.updated_at or datetime.min.replace(tzinfo=timezone.utc), item.template_id, item.version),
                reverse=True,
            )
            if template_id:
                ordered = [item for item in ordered if item.template_id == template_id]
            return ordered[offset : offset + limit]

        where_clause = "template_id = %s" if template_id else "1=1"
        params: list[object] = [limit, offset]
        if template_id:
            params = [template_id, limit, offset]

        psycopg, dict_row = _import_psycopg()
        with psycopg.connect(self._dsn, autocommit=True, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    SELECT template_id, version, metadata, payload, created_at, updated_at
                    FROM {self._schema}.document_templates
                    WHERE {where_clause}
                    ORDER BY updated_at DESC, template_id DESC, version DESC
                    LIMIT %s
                    OFFSET %s
                    """,
                    tuple(params),
                )
                rows = cur.fetchall()

        return [_row_to_template_record(row) for row in rows]


def _row_to_template_record(row: dict[str, Any]) -> TemplateRecord:
    return TemplateRecord(
        template_id=str(row["template_id"]),
        version=str(row["version"]),
        template_spec=TemplateSpec.model_validate(_json_payload(row["payload"])),
        metadata=dict(_json_payload(row["metadata"]) or {}),
        created_at=row.get("created_at"),
        updated_at=row.get("updated_at"),
    )


def _json_payload(value: Any) -> Any:
    if isinstance(value, str):
        return json.loads(value)
    return value


def _import_psycopg():
    try:
        import psycopg
        from psycopg.rows import dict_row
    except ImportError as exc:
        raise RuntimeError("psycopg is required for PostgreSQL template store") from exc
    return psycopg, dict_row


def _validate_page(*, limit: int, offset: int) -> None:
    if limit < 1 or limit > 200:
        raise ValueError("limit должен быть в диапазоне 1..200")
    if offset < 0:
        raise ValueError("offset должен быть >= 0")
