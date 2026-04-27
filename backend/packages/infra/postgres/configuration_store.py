from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from application.configuration_library_service import ConfigurationRecord
from infra.postgres.config import PostgresSettings, validate_identifier


class PostgresConfigurationStore:
    """Versioned configuration library store with PostgreSQL and fallback modes."""

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
        self._configs: dict[tuple[str, str], ConfigurationRecord] = {}

        if not self._use_fallback and not self._dsn:
            raise ValueError("DSN обязателен для PostgreSQL configuration store")

    @classmethod
    def from_settings(
        cls,
        settings: PostgresSettings,
        *,
        use_fallback_if_unset: bool | None = None,
    ) -> "PostgresConfigurationStore":
        fallback_enabled = settings.allow_fallback_persistence if use_fallback_if_unset is None else use_fallback_if_unset
        return cls(dsn=settings.dsn, schema=settings.schema, use_fallback_if_unset=fallback_enabled)

    def upsert_config(
        self,
        *,
        config_id: str,
        version: str,
        config_type: str,
        title: str | None,
        payload: dict[str, Any],
        metadata: dict[str, Any] | None = None,
        tags: list[str] | None = None,
    ) -> str:
        resolved_metadata = dict(metadata or {})
        resolved_tags = list(tags or [])

        if self._use_fallback:
            now_utc = datetime.now(timezone.utc)
            key = (config_id, version)
            current = self._configs.get(key)
            self._configs[key] = ConfigurationRecord(
                config_id=config_id,
                version=version,
                config_type=config_type,
                title=title,
                payload=dict(payload),
                metadata=resolved_metadata,
                tags=resolved_tags,
                created_at=current.created_at if current is not None else now_utc,
                updated_at=now_utc,
            )
            return config_id

        psycopg, dict_row = _import_psycopg()
        with psycopg.connect(self._dsn, autocommit=True, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    INSERT INTO {self._schema}.configuration_library (
                        config_id,
                        version,
                        config_type,
                        title,
                        tags,
                        metadata,
                        payload
                    )
                    VALUES (%s, %s, %s, %s, %s::jsonb, %s::jsonb, %s::jsonb)
                    ON CONFLICT (config_id, version)
                    DO UPDATE SET
                        config_type = EXCLUDED.config_type,
                        title = EXCLUDED.title,
                        tags = EXCLUDED.tags,
                        metadata = EXCLUDED.metadata,
                        payload = EXCLUDED.payload,
                        updated_at = now()
                    """,
                    (
                        config_id,
                        version,
                        config_type,
                        title,
                        json.dumps(resolved_tags, ensure_ascii=False),
                        json.dumps(resolved_metadata, ensure_ascii=False),
                        json.dumps(payload, ensure_ascii=False),
                    ),
                )
        return config_id

    def get_config(self, config_id: str, version: str | None = None) -> ConfigurationRecord:
        if self._use_fallback:
            if version is not None:
                item = self._configs.get((config_id, version))
                if item is None:
                    raise KeyError(f"Configuration {config_id}:{version} не найдена")
                return item

            candidates = [item for (stored_id, _), item in self._configs.items() if stored_id == config_id]
            if not candidates:
                raise KeyError(f"Configuration {config_id} не найдена")
            return sorted(
                candidates,
                key=lambda item: (item.updated_at or datetime.min.replace(tzinfo=timezone.utc), item.version),
                reverse=True,
            )[0]

        psycopg, dict_row = _import_psycopg()
        query = (
            f"""
            SELECT config_id, version, config_type, title, tags, metadata, payload, created_at, updated_at
            FROM {self._schema}.configuration_library
            WHERE config_id = %s AND version = %s
            """
            if version is not None
            else f"""
            SELECT config_id, version, config_type, title, tags, metadata, payload, created_at, updated_at
            FROM {self._schema}.configuration_library
            WHERE config_id = %s
            ORDER BY updated_at DESC, version DESC
            LIMIT 1
            """
        )
        params = (config_id, version) if version is not None else (config_id,)

        with psycopg.connect(self._dsn, autocommit=True, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
                row = cur.fetchone()

        if row is None:
            raise KeyError(f"Configuration {config_id}:{version or 'latest'} не найдена")
        return _row_to_configuration_record(row)

    def list_configs(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
        config_id: str | None = None,
        config_type: str | None = None,
        tag: str | None = None,
    ) -> list[ConfigurationRecord]:
        _validate_page(limit=limit, offset=offset)

        if self._use_fallback:
            ordered = sorted(
                self._configs.values(),
                key=lambda item: (item.updated_at or datetime.min.replace(tzinfo=timezone.utc), item.config_id, item.version),
                reverse=True,
            )
            if config_id is not None:
                ordered = [item for item in ordered if item.config_id == config_id]
            if config_type is not None:
                ordered = [item for item in ordered if item.config_type == config_type]
            if tag is not None:
                ordered = [item for item in ordered if tag in item.tags]
            return ordered[offset : offset + limit]

        where_clauses = ["1=1"]
        params: list[object] = []
        if config_id is not None:
            where_clauses.append("config_id = %s")
            params.append(config_id)
        if config_type is not None:
            where_clauses.append("config_type = %s")
            params.append(config_type)
        if tag is not None:
            where_clauses.append("tags ? %s")
            params.append(tag)
        params.extend([limit, offset])

        psycopg, dict_row = _import_psycopg()
        with psycopg.connect(self._dsn, autocommit=True, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    SELECT config_id, version, config_type, title, tags, metadata, payload, created_at, updated_at
                    FROM {self._schema}.configuration_library
                    WHERE {' AND '.join(where_clauses)}
                    ORDER BY updated_at DESC, config_id DESC, version DESC
                    LIMIT %s
                    OFFSET %s
                    """,
                    tuple(params),
                )
                rows = cur.fetchall()

        return [_row_to_configuration_record(row) for row in rows]

    def count_configs(
        self,
        *,
        config_id: str | None = None,
        config_type: str | None = None,
        tag: str | None = None,
    ) -> int:
        if self._use_fallback:
            records = list(self._configs.values())
            if config_id is not None:
                records = [item for item in records if item.config_id == config_id]
            if config_type is not None:
                records = [item for item in records if item.config_type == config_type]
            if tag is not None:
                records = [item for item in records if tag in item.tags]
            return len(records)

        where_clauses = ["1=1"]
        params: list[object] = []
        if config_id is not None:
            where_clauses.append("config_id = %s")
            params.append(config_id)
        if config_type is not None:
            where_clauses.append("config_type = %s")
            params.append(config_type)
        if tag is not None:
            where_clauses.append("tags ? %s")
            params.append(tag)

        psycopg, dict_row = _import_psycopg()
        with psycopg.connect(self._dsn, autocommit=True, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    SELECT COUNT(*) AS total
                    FROM {self._schema}.configuration_library
                    WHERE {' AND '.join(where_clauses)}
                    """,
                    tuple(params),
                )
                row = cur.fetchone()

        return int(row["total"] if row is not None else 0)


def _validate_page(*, limit: int, offset: int) -> None:
    if limit < 1:
        raise ValueError("limit должен быть >= 1")
    if offset < 0:
        raise ValueError("offset должен быть >= 0")


def _import_psycopg():
    try:
        import psycopg
        from psycopg.rows import dict_row
    except Exception as exc:  # pragma: no cover
        raise RuntimeError(
            "Для PostgreSQL режима требуется установленный psycopg. "
            "Установите зависимость 'psycopg[binary]'."
        ) from exc
    return psycopg, dict_row


def _json_payload(value: Any) -> Any:
    if isinstance(value, str):
        return json.loads(value)
    return value


def _row_to_configuration_record(row: dict[str, Any]) -> ConfigurationRecord:
    return ConfigurationRecord(
        config_id=str(row["config_id"]),
        version=str(row["version"]),
        config_type=str(row.get("config_type") or "generic"),
        title=row.get("title"),
        tags=list(_json_payload(row.get("tags")) or []),
        metadata=dict(_json_payload(row.get("metadata")) or {}),
        payload=dict(_json_payload(row.get("payload")) or {}),
        created_at=row.get("created_at"),
        updated_at=row.get("updated_at"),
    )
