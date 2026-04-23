from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from application.canonical_document_service import KnowledgeBlockRecord
from infra.postgres.config import PostgresSettings, validate_identifier
from schemas.documents.contracts import CanonicalDocument


class PostgresCanonicalDocumentStore:
    """Canonical document store backed by PostgreSQL with in-memory fallback."""

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
        self._blocks: dict[str, KnowledgeBlockRecord] = {}

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
            now_utc = datetime.now(timezone.utc)
            current = self._documents.get(document.doc_id)
            self._documents[document.doc_id] = {
                "document": document.model_dump(mode="json"),
                "created_at": current["created_at"] if current else now_utc,
                "updated_at": now_utc,
            }
            self._replace_blocks_fallback(document=document, now_utc=now_utc)
            return document.doc_id

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
                    (
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
                    ),
                )
                cur.execute(
                    f"DELETE FROM {self._schema}.knowledge_blocks WHERE doc_id = %s",
                    (document.doc_id,),
                )
                for block in document.content_blocks:
                    block_ref = _build_block_ref(document.doc_id, document.version, block.block_id)
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
                        (
                            block_ref,
                            document.doc_id,
                            document.version,
                            block.block_id,
                            block.block_type,
                            block.text,
                            json.dumps(block.heading_path, ensure_ascii=False),
                            json.dumps(block.metadata, ensure_ascii=False),
                        ),
                    )
        return document.doc_id

    def get_document(self, doc_id: str) -> CanonicalDocument:
        if self._use_fallback:
            item = self._documents.get(doc_id)
            if item is None:
                raise KeyError(f"Canonical document {doc_id} не найден")
            return CanonicalDocument.model_validate(item["document"])

        psycopg, dict_row = _import_psycopg()
        with psycopg.connect(self._dsn, autocommit=True, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"SELECT payload FROM {self._schema}.canonical_documents WHERE doc_id = %s",
                    (doc_id,),
                )
                row = cur.fetchone()

        if row is None:
            raise KeyError(f"Canonical document {doc_id} не найден")
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

    def list_blocks(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
        doc_id: str | None = None,
        block_type: str | None = None,
    ) -> list[KnowledgeBlockRecord]:
        _validate_page(limit=limit, offset=offset)

        if self._use_fallback:
            ordered = sorted(
                self._blocks.values(),
                key=lambda item: (item.updated_at or datetime.min.replace(tzinfo=timezone.utc), item.block_ref),
                reverse=True,
            )
            if doc_id:
                ordered = [item for item in ordered if item.doc_id == doc_id]
            if block_type:
                ordered = [item for item in ordered if item.block_type == block_type]
            return ordered[offset : offset + limit]

        where_clauses = ["1=1"]
        params: list[object] = []
        if doc_id:
            where_clauses.append("doc_id = %s")
            params.append(doc_id)
        if block_type:
            where_clauses.append("block_type = %s")
            params.append(block_type)
        params.extend([limit, offset])

        psycopg, dict_row = _import_psycopg()
        with psycopg.connect(self._dsn, autocommit=True, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    SELECT block_ref, doc_id, version, block_id, block_type, text, heading_path, metadata, created_at, updated_at
                    FROM {self._schema}.knowledge_blocks
                    WHERE {" AND ".join(where_clauses)}
                    ORDER BY updated_at DESC, block_ref DESC
                    LIMIT %s
                    OFFSET %s
                    """,
                    tuple(params),
                )
                rows = cur.fetchall()

        return [_row_to_block_record(row) for row in rows]

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
                created_at=now_utc,
                updated_at=now_utc,
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


def _row_to_block_record(row: dict[str, Any]) -> KnowledgeBlockRecord:
    return KnowledgeBlockRecord(
        block_ref=row["block_ref"],
        doc_id=row["doc_id"],
        version=row["version"],
        block_id=row["block_id"],
        block_type=row["block_type"],
        text=row["text"],
        heading_path=_json_payload(row["heading_path"]),
        metadata=_json_payload(row["metadata"]),
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
