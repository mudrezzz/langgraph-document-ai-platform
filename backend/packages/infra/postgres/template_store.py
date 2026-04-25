from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from application.template_library_service import TemplateRecord, TemplateStatus
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

    def upsert_template(
        self,
        template_spec: TemplateSpec,
        *,
        metadata: dict | None = None,
        status: TemplateStatus | None = None,
    ) -> str:
        resolved_status: TemplateStatus = status or "draft"
        governance_metadata = _merge_governance_metadata(
            existing_metadata=self._templates.get((template_spec.template_id, template_spec.version)).metadata
            if self._use_fallback and (template_spec.template_id, template_spec.version) in self._templates
            else None,
            patch_metadata=metadata,
            next_status=resolved_status,
            reason="upsert",
            actor="template-store",
            append_history=False,
        )
        if self._use_fallback:
            now_utc = datetime.now(timezone.utc)
            key = (template_spec.template_id, template_spec.version)
            current = self._templates.get(key)
            self._templates[key] = TemplateRecord(
                template_id=template_spec.template_id,
                version=template_spec.version,
                status=resolved_status,
                template_spec=template_spec,
                metadata=governance_metadata,
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
                        status,
                        metadata,
                        payload
                    )
                    VALUES (%s, %s, %s, %s::jsonb, %s::jsonb)
                    ON CONFLICT (template_id, version)
                    DO UPDATE SET
                        status = EXCLUDED.status,
                        metadata = EXCLUDED.metadata,
                        payload = EXCLUDED.payload,
                        updated_at = now()
                    """,
                    (
                        template_spec.template_id,
                        template_spec.version,
                        resolved_status,
                        json.dumps(governance_metadata, ensure_ascii=False),
                        json.dumps(payload, ensure_ascii=False),
                    ),
                )
        return template_spec.template_id

    def get_template(
        self,
        template_id: str,
        version: str | None = None,
        *,
        published_only: bool = False,
        allow_archived: bool = True,
    ) -> TemplateRecord:
        if self._use_fallback:
            if version is not None:
                item = self._templates.get((template_id, version))
                if item is None or (not allow_archived and item.status == "archived"):
                    raise KeyError(f"Template {template_id}:{version} не найден")
                return item

            candidates = [item for key, item in self._templates.items() if key[0] == template_id]
            if published_only:
                candidates = [item for item in candidates if item.status == "published"]
            if not allow_archived:
                candidates = [item for item in candidates if item.status != "archived"]
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
            SELECT template_id, version, status, metadata, payload, created_at, updated_at
            FROM {self._schema}.document_templates
            WHERE template_id = %s AND version = %s AND (%s = TRUE OR status <> 'archived')
            """
            if version is not None
            else f"""
            SELECT template_id, version, status, metadata, payload, created_at, updated_at
            FROM {self._schema}.document_templates
            WHERE template_id = %s
              AND (%s = FALSE OR status = 'published')
              AND (%s = TRUE OR status <> 'archived')
            ORDER BY updated_at DESC, version DESC
            LIMIT 1
            """
        )
        params = (template_id, version, allow_archived) if version is not None else (template_id, published_only, allow_archived)

        with psycopg.connect(self._dsn, autocommit=True, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
                row = cur.fetchone()

        if row is None:
            raise KeyError(f"Template {template_id}:{version or 'latest'} не найден")
        return _row_to_template_record(row)

    def publish_template(self, template_id: str, version: str) -> TemplateRecord:
        return self.set_template_status(template_id, version, "published")

    def set_template_status(
        self,
        template_id: str,
        version: str,
        status: TemplateStatus,
        *,
        reason: str | None = None,
        actor: str | None = None,
        metadata: dict | None = None,
    ) -> TemplateRecord:
        if self._use_fallback:
            key = (template_id, version)
            current = self._templates.get(key)
            if current is None:
                raise KeyError(f"Template {template_id}:{version} не найден")
            now_utc = datetime.now(timezone.utc)

            if status == "published":
                for existing_key, existing_record in list(self._templates.items()):
                    if existing_key[0] != template_id or existing_key == key:
                        continue
                    if existing_record.status != "published":
                        continue
                    demoted_metadata = _merge_governance_metadata(
                        existing_metadata=existing_record.metadata,
                        patch_metadata=None,
                        next_status="draft",
                        reason=f"superseded_by_publish:{version}",
                        actor=actor or "template-store",
                        append_history=True,
                    )
                    self._templates[existing_key] = existing_record.model_copy(
                        update={
                            "status": "draft",
                            "metadata": demoted_metadata,
                            "updated_at": now_utc,
                        }
                    )

            updated_metadata = _merge_governance_metadata(
                existing_metadata=current.metadata,
                patch_metadata=metadata,
                next_status=status,
                reason=reason,
                actor=actor,
                append_history=True,
            )
            updated = current.model_copy(
                update={
                    "status": status,
                    "metadata": updated_metadata,
                    "updated_at": now_utc,
                }
            )
            self._templates[key] = updated
            return updated

        psycopg, dict_row = _import_psycopg()
        with psycopg.connect(self._dsn, autocommit=True, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    SELECT template_id, version, status, metadata, payload, created_at, updated_at
                    FROM {self._schema}.document_templates
                    WHERE template_id = %s AND version = %s
                    """,
                    (template_id, version),
                )
                current_row = cur.fetchone()
                if current_row is None:
                    raise KeyError(f"Template {template_id}:{version} не найден")

                if status == "published":
                    cur.execute(
                        f"""
                        SELECT template_id, version, status, metadata, payload, created_at, updated_at
                        FROM {self._schema}.document_templates
                        WHERE template_id = %s AND status = 'published' AND version <> %s
                        """,
                        (template_id, version),
                    )
                    previous_rows = cur.fetchall()
                    for previous_row in previous_rows:
                        demoted_metadata = _merge_governance_metadata(
                            existing_metadata=_json_payload(previous_row["metadata"]),
                            patch_metadata=None,
                            next_status="draft",
                            reason=f"superseded_by_publish:{version}",
                            actor=actor or "template-store",
                            append_history=True,
                        )
                        cur.execute(
                            f"""
                            UPDATE {self._schema}.document_templates
                            SET status = 'draft', metadata = %s::jsonb, updated_at = now()
                            WHERE template_id = %s AND version = %s
                            """,
                            (
                                json.dumps(demoted_metadata, ensure_ascii=False),
                                str(previous_row["template_id"]),
                                str(previous_row["version"]),
                            ),
                        )

                updated_metadata = _merge_governance_metadata(
                    existing_metadata=_json_payload(current_row["metadata"]),
                    patch_metadata=metadata,
                    next_status=status,
                    reason=reason,
                    actor=actor,
                    append_history=True,
                )
                cur.execute(
                    f"""
                    UPDATE {self._schema}.document_templates
                    SET status = %s, metadata = %s::jsonb, updated_at = now()
                    WHERE template_id = %s AND version = %s
                    RETURNING template_id, version, status, metadata, payload, created_at, updated_at
                    """,
                    (
                        status,
                        json.dumps(updated_metadata, ensure_ascii=False),
                        template_id,
                        version,
                    ),
                )
                row = cur.fetchone()

        if row is None:
            raise KeyError(f"Template {template_id}:{version} не найден")
        return _row_to_template_record(row)

    def list_templates(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
        template_id: str | None = None,
        status: TemplateStatus | None = None,
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
            if status is not None:
                ordered = [item for item in ordered if item.status == status]
            return ordered[offset : offset + limit]

        filters: list[str] = []
        params: list[object] = []
        if template_id:
            filters.append("template_id = %s")
            params.append(template_id)
        if status is not None:
            filters.append("status = %s")
            params.append(status)
        where_clause = " AND ".join(filters) if filters else "1=1"
        params.extend([limit, offset])

        psycopg, dict_row = _import_psycopg()
        with psycopg.connect(self._dsn, autocommit=True, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    SELECT template_id, version, status, metadata, payload, created_at, updated_at
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
        status=str(row.get("status") or "draft"),
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


def _merge_governance_metadata(
    *,
    existing_metadata: dict[str, Any] | None,
    patch_metadata: dict[str, Any] | None,
    next_status: str,
    reason: str | None,
    actor: str | None,
    append_history: bool,
) -> dict[str, Any]:
    merged = dict(existing_metadata or {})
    if patch_metadata:
        merged.update(dict(patch_metadata))

    governance = dict(merged.get("governance") or {})
    history = list(governance.get("status_history") or [])
    timestamp = datetime.now(timezone.utc).isoformat()
    governance.update(
        {
            "current_status": next_status,
            "updated_at": timestamp,
            "updated_by": actor or governance.get("updated_by") or "system",
        }
    )
    if reason:
        governance["reason"] = reason
    if append_history:
        history.append(
            {
                "status": next_status,
                "at": timestamp,
                "reason": reason,
                "actor": actor or "system",
            }
        )
    governance["status_history"] = history
    merged["governance"] = governance
    return merged
