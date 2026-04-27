from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from application.canonical_document_service import CanonicalDocumentVersionRecord, KnowledgeBlockRecord
from infra.postgres.config import PostgresSettings, validate_identifier
from schemas.documents.contracts import CanonicalDocument


class PostgresCanonicalDocumentStore:
    """Canonical document store with latest read-model and version history."""

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
        self._documents: dict[str, dict[str, Any]] = {}
        self._document_versions: dict[tuple[str, str], dict[str, Any]] = {}
        self._blocks: dict[str, KnowledgeBlockRecord] = {}
        self._block_versions: dict[str, KnowledgeBlockRecord] = {}

        if not self._use_fallback and not self._dsn:
            raise ValueError("DSN обязателен для PostgreSQL canonical document store")

    @classmethod
    def from_settings(
        cls,
        settings: PostgresSettings,
        *,
        use_fallback_if_unset: bool | None = None,
    ) -> "PostgresCanonicalDocumentStore":
        fallback_enabled = settings.allow_fallback_persistence if use_fallback_if_unset is None else use_fallback_if_unset
        return cls(dsn=settings.dsn, schema=settings.schema, use_fallback_if_unset=fallback_enabled)

    def save_document(self, document: CanonicalDocument) -> str:
        if self._use_fallback:
            self._save_document_fallback(document)
            return document.doc_id

        self._save_document_postgres(document)
        return document.doc_id

    def get_document(self, doc_id: str, version: str | None = None) -> CanonicalDocument:
        if self._use_fallback:
            if version is None:
                item = self._documents.get(doc_id)
            else:
                item = self._document_versions.get((doc_id, version))
            if item is None:
                raise KeyError(f"Canonical document {doc_id}@{version or 'latest'} не найден")
            return CanonicalDocument.model_validate(item["document"])

        psycopg, dict_row = _import_psycopg()
        table_name = "canonical_documents" if version is None else "canonical_document_versions"
        where_clause = "doc_id = %s" if version is None else "doc_id = %s AND version = %s"
        params: tuple[object, ...] = (doc_id,) if version is None else (doc_id, version)

        with psycopg.connect(self._dsn, autocommit=True, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"SELECT payload FROM {self._schema}.{table_name} WHERE {where_clause}",
                    params,
                )
                row = cur.fetchone()

        if row is None:
            raise KeyError(f"Canonical document {doc_id}@{version or 'latest'} не найден")
        return CanonicalDocument.model_validate(_json_payload(row["payload"]))

    def list_documents(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
        file_type: str | None = None,
    ) -> list[CanonicalDocument]:
        _validate_page(limit=limit, offset=offset)

        if self._use_fallback:
            ordered = sorted(
                self._documents.values(),
                key=lambda item: (item["updated_at"], item["document"]["doc_id"]),
                reverse=True,
            )
            if file_type:
                ordered = [item for item in ordered if item["document"].get("file_type") == file_type]
            return [CanonicalDocument.model_validate(item["document"]) for item in ordered[offset : offset + limit]]

        where_clause = "file_type = %s" if file_type else "1=1"
        params: list[object] = [limit, offset]
        if file_type:
            params = [file_type, limit, offset]

        psycopg, dict_row = _import_psycopg()
        with psycopg.connect(self._dsn, autocommit=True, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    SELECT payload
                    FROM {self._schema}.canonical_documents
                    WHERE {where_clause}
                    ORDER BY updated_at DESC, doc_id DESC
                    LIMIT %s
                    OFFSET %s
                    """,
                    tuple(params),
                )
                rows = cur.fetchall()

        return [CanonicalDocument.model_validate(_json_payload(row["payload"])) for row in rows]

    def list_versions(
        self,
        doc_id: str,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> list[CanonicalDocumentVersionRecord]:
        _validate_page(limit=limit, offset=offset)
        latest_version = self._latest_version_for_doc(doc_id)

        if self._use_fallback:
            ordered = sorted(
                [
                    item
                    for (stored_doc_id, _), item in self._document_versions.items()
                    if stored_doc_id == doc_id
                ],
                key=lambda item: (item["updated_at"], item["document"]["version"]),
                reverse=True,
            )
            return [
                _fallback_version_record(item=item, latest_version=latest_version)
                for item in ordered[offset : offset + limit]
            ]

        psycopg, dict_row = _import_psycopg()
        with psycopg.connect(self._dsn, autocommit=True, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    SELECT doc_id, version, source_path, file_type, metadata_profile, created_at, updated_at
                    FROM {self._schema}.canonical_document_versions
                    WHERE doc_id = %s
                    ORDER BY updated_at DESC, version DESC
                    LIMIT %s
                    OFFSET %s
                    """,
                    (doc_id, limit, offset),
                )
                rows = cur.fetchall()

        return [_row_to_version_record(row, latest_version=latest_version) for row in rows]

    def list_blocks(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
        doc_id: str | None = None,
        version: str | None = None,
        block_type: str | None = None,
    ) -> list[KnowledgeBlockRecord]:
        _validate_page(limit=limit, offset=offset)

        if self._use_fallback:
            source = self._block_versions if version is not None else self._blocks
            ordered = sorted(
                source.values(),
                key=lambda item: (item.updated_at or datetime.min.replace(tzinfo=timezone.utc), item.block_ref),
                reverse=True,
            )
            if doc_id:
                ordered = [item for item in ordered if item.doc_id == doc_id]
            if version is not None:
                ordered = [item for item in ordered if item.version == version]
            if block_type:
                ordered = [item for item in ordered if item.block_type == block_type]
            latest_map = self._latest_versions_map()
            return [
                item.model_copy(update={"is_latest": latest_map.get(item.doc_id) == item.version})
                for item in ordered[offset : offset + limit]
            ]

        table_name = "knowledge_block_versions" if version is not None else "knowledge_blocks"
        where_clauses = ["1=1"]
        params: list[object] = []
        if doc_id:
            where_clauses.append("doc_id = %s")
            params.append(doc_id)
        if version is not None:
            where_clauses.append("version = %s")
            params.append(version)
        if block_type:
            where_clauses.append("block_type = %s")
            params.append(block_type)
        params.extend([limit, offset])
        latest_versions = self._latest_versions_map()

        psycopg, dict_row = _import_psycopg()
        with psycopg.connect(self._dsn, autocommit=True, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    SELECT block_ref, doc_id, version, block_id, block_type, text, heading_path, metadata, created_at, updated_at
                    FROM {self._schema}.{table_name}
                    WHERE {' AND '.join(where_clauses)}
                    ORDER BY updated_at DESC, block_ref DESC
                    LIMIT %s
                    OFFSET %s
                    """,
                    tuple(params),
                )
                rows = cur.fetchall()

        return [_row_to_block_record(row, latest_versions=latest_versions) for row in rows]

    def _save_document_fallback(self, document: CanonicalDocument) -> None:
        now_utc = datetime.now(timezone.utc)
        latest_current = self._documents.get(document.doc_id)
        latest_created_at = (
            latest_current["created_at"]
            if latest_current and latest_current["document"].get("version") == document.version
            else now_utc
        )
        version_key = (document.doc_id, document.version)
        current_version = self._document_versions.get(version_key)

        payload = document.model_dump(mode="json")
        self._documents[document.doc_id] = {
            "document": payload,
            "created_at": latest_created_at,
            "updated_at": now_utc,
        }
        self._document_versions[version_key] = {
            "document": payload,
            "created_at": current_version["created_at"] if current_version else now_utc,
            "updated_at": now_utc,
        }
        self._replace_blocks_fallback(document=document, now_utc=now_utc)
        self._replace_version_blocks_fallback(document=document, now_utc=now_utc)

    def _save_document_postgres(self, document: CanonicalDocument) -> None:
        psycopg, dict_row = _import_psycopg()
        payload = document.model_dump(mode="json")

        with psycopg.connect(self._dsn, autocommit=True, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    INSERT INTO {self._schema}.canonical_documents (
                        doc_id,
                        version,
                        source_path,
                        file_type,
                        metadata_profile,
                        structure_tree,
                        extracted_tables,
                        section_summaries,
                        quality_flags,
                        payload
                    )
                    VALUES (%s, %s, %s, %s, %s::jsonb, %s::jsonb, %s::jsonb, %s::jsonb, %s::jsonb, %s::jsonb)
                    ON CONFLICT (doc_id)
                    DO UPDATE SET
                        version = EXCLUDED.version,
                        source_path = EXCLUDED.source_path,
                        file_type = EXCLUDED.file_type,
                        metadata_profile = EXCLUDED.metadata_profile,
                        structure_tree = EXCLUDED.structure_tree,
                        extracted_tables = EXCLUDED.extracted_tables,
                        section_summaries = EXCLUDED.section_summaries,
                        quality_flags = EXCLUDED.quality_flags,
                        payload = EXCLUDED.payload,
                        updated_at = now()
                    """,
                    _document_write_params(document, payload),
                )
                cur.execute(
                    f"""
                    INSERT INTO {self._schema}.canonical_document_versions (
                        doc_id,
                        version,
                        source_path,
                        file_type,
                        metadata_profile,
                        structure_tree,
                        extracted_tables,
                        section_summaries,
                        quality_flags,
                        payload
                    )
                    VALUES (%s, %s, %s, %s, %s::jsonb, %s::jsonb, %s::jsonb, %s::jsonb, %s::jsonb, %s::jsonb)
                    ON CONFLICT (doc_id, version)
                    DO UPDATE SET
                        source_path = EXCLUDED.source_path,
                        file_type = EXCLUDED.file_type,
                        metadata_profile = EXCLUDED.metadata_profile,
                        structure_tree = EXCLUDED.structure_tree,
                        extracted_tables = EXCLUDED.extracted_tables,
                        section_summaries = EXCLUDED.section_summaries,
                        quality_flags = EXCLUDED.quality_flags,
                        payload = EXCLUDED.payload,
                        updated_at = now()
                    """,
                    _document_write_params(document, payload),
                )
                cur.execute(
                    f"DELETE FROM {self._schema}.knowledge_blocks WHERE doc_id = %s",
                    (document.doc_id,),
                )
                cur.execute(
                    f"DELETE FROM {self._schema}.knowledge_block_versions WHERE doc_id = %s AND version = %s",
                    (document.doc_id, document.version),
                )
                for block in document.content_blocks:
                    block_ref = _build_block_ref(document.doc_id, document.version, block.block_id)
                    latest_params = _block_write_params(document=document, block=block, block_ref=block_ref)
                    cur.execute(
                        f"""
                        INSERT INTO {self._schema}.knowledge_blocks (
                            block_ref,
                            doc_id,
                            version,
                            block_id,
                            block_type,
                            text,
                            heading_path,
                            metadata
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb, %s::jsonb)
                        ON CONFLICT (block_ref)
                        DO UPDATE SET
                            block_type = EXCLUDED.block_type,
                            text = EXCLUDED.text,
                            heading_path = EXCLUDED.heading_path,
                            metadata = EXCLUDED.metadata,
                            updated_at = now()
                        """,
                        latest_params,
                    )
                    cur.execute(
                        f"""
                        INSERT INTO {self._schema}.knowledge_block_versions (
                            block_ref,
                            doc_id,
                            version,
                            block_id,
                            block_type,
                            text,
                            heading_path,
                            metadata
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb, %s::jsonb)
                        ON CONFLICT (block_ref)
                        DO UPDATE SET
                            block_type = EXCLUDED.block_type,
                            text = EXCLUDED.text,
                            heading_path = EXCLUDED.heading_path,
                            metadata = EXCLUDED.metadata,
                            updated_at = now()
                        """,
                        latest_params,
                    )

    def _replace_blocks_fallback(self, *, document: CanonicalDocument, now_utc: datetime) -> None:
        stale_refs = [block_ref for block_ref, block in self._blocks.items() if block.doc_id == document.doc_id]
        for block_ref in stale_refs:
            del self._blocks[block_ref]
        for block in document.content_blocks:
            block_ref = _build_block_ref(document.doc_id, document.version, block.block_id)
            self._blocks[block_ref] = KnowledgeBlockRecord(
                block_ref=block_ref,
                doc_id=document.doc_id,
                version=document.version,
                block_id=block.block_id,
                block_type=block.block_type,
                text=block.text,
                heading_path=list(block.heading_path),
                metadata=dict(block.metadata),
                is_latest=True,
                created_at=now_utc,
                updated_at=now_utc,
            )

    def _replace_version_blocks_fallback(self, *, document: CanonicalDocument, now_utc: datetime) -> None:
        stale_refs = [
            block_ref
            for block_ref, block in self._block_versions.items()
            if block.doc_id == document.doc_id and block.version == document.version
        ]
        for block_ref in stale_refs:
            del self._block_versions[block_ref]
        for block in document.content_blocks:
            block_ref = _build_block_ref(document.doc_id, document.version, block.block_id)
            self._block_versions[block_ref] = KnowledgeBlockRecord(
                block_ref=block_ref,
                doc_id=document.doc_id,
                version=document.version,
                block_id=block.block_id,
                block_type=block.block_type,
                text=block.text,
                heading_path=list(block.heading_path),
                metadata=dict(block.metadata),
                is_latest=True,
                created_at=now_utc,
                updated_at=now_utc,
            )

    def _latest_version_for_doc(self, doc_id: str) -> str | None:
        if self._use_fallback:
            latest = self._documents.get(doc_id)
            if latest is None:
                return None
            return str(latest["document"].get("version") or "") or None

        psycopg, dict_row = _import_psycopg()
        with psycopg.connect(self._dsn, autocommit=True, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"SELECT version FROM {self._schema}.canonical_documents WHERE doc_id = %s",
                    (doc_id,),
                )
                row = cur.fetchone()
        if row is None:
            return None
        return str(row["version"])

    def _latest_versions_map(self) -> dict[str, str]:
        if self._use_fallback:
            return {
                doc_id: str(item["document"].get("version") or "")
                for doc_id, item in self._documents.items()
            }

        psycopg, dict_row = _import_psycopg()
        with psycopg.connect(self._dsn, autocommit=True, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"SELECT doc_id, version FROM {self._schema}.canonical_documents",
                )
                rows = cur.fetchall()
        return {str(row["doc_id"]): str(row["version"]) for row in rows}


def _document_write_params(document: CanonicalDocument, payload: dict[str, Any]) -> tuple[object, ...]:
    return (
        document.doc_id,
        document.version,
        document.source_path,
        document.file_type,
        json.dumps(payload["metadata_profile"], ensure_ascii=False),
        json.dumps(payload["structure_tree"], ensure_ascii=False),
        json.dumps(payload["extracted_tables"], ensure_ascii=False),
        json.dumps(payload["section_summaries"], ensure_ascii=False),
        json.dumps(payload["quality_flags"], ensure_ascii=False),
        json.dumps(payload, ensure_ascii=False),
    )


def _block_write_params(*, document: CanonicalDocument, block: Any, block_ref: str) -> tuple[object, ...]:
    return (
        block_ref,
        document.doc_id,
        document.version,
        block.block_id,
        block.block_type,
        block.text,
        json.dumps(block.heading_path, ensure_ascii=False),
        json.dumps(block.metadata, ensure_ascii=False),
    )


def _build_block_ref(doc_id: str, version: str, block_id: str) -> str:
    return f"{doc_id}:{version}:{block_id}"


def _validate_page(*, limit: int, offset: int) -> None:
    if limit < 1:
        raise ValueError("limit должен быть >= 1")
    if offset < 0:
        raise ValueError("offset должен быть >= 0")


def _json_payload(value: Any) -> Any:
    if isinstance(value, str):
        return json.loads(value)
    return value


def _row_to_block_record(row: dict[str, Any], *, latest_versions: dict[str, str]) -> KnowledgeBlockRecord:
    doc_id = str(row["doc_id"])
    version = str(row["version"])
    return KnowledgeBlockRecord(
        block_ref=row["block_ref"],
        doc_id=doc_id,
        version=version,
        block_id=row["block_id"],
        block_type=row["block_type"],
        text=row["text"],
        heading_path=_json_payload(row["heading_path"]),
        metadata=_json_payload(row["metadata"]),
        is_latest=latest_versions.get(doc_id) == version,
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _fallback_version_record(*, item: dict[str, Any], latest_version: str | None) -> CanonicalDocumentVersionRecord:
    document = item["document"]
    version = str(document.get("version") or "")
    return CanonicalDocumentVersionRecord(
        doc_id=document["doc_id"],
        version=version,
        source_path=document["source_path"],
        file_type=document["file_type"],
        metadata_profile=dict(document.get("metadata_profile") or {}),
        is_latest=latest_version == version,
        created_at=item["created_at"],
        updated_at=item["updated_at"],
    )


def _row_to_version_record(row: dict[str, Any], *, latest_version: str | None) -> CanonicalDocumentVersionRecord:
    version = str(row["version"])
    return CanonicalDocumentVersionRecord(
        doc_id=row["doc_id"],
        version=version,
        source_path=row["source_path"],
        file_type=row["file_type"],
        metadata_profile=_json_payload(row["metadata_profile"]),
        is_latest=latest_version == version,
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
