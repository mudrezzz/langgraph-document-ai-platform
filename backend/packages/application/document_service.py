from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from application.errors import DocumentNotFoundError
from infra.postgres.document_repository import PostgresDocumentRepository


class DocumentRecord(BaseModel):
    """Внутренняя запись документа для application-слоя."""

    doc_id: str
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime | None = None
    updated_at: datetime | None = None


class DocumentListPage(BaseModel):
    """Страница документов для list-операции."""

    items: list[DocumentRecord] = Field(default_factory=list)
    limit: int
    offset: int
    total_returned: int


class DocumentApplicationService:
    """Application service для операций document repository."""

    def __init__(self, repository: PostgresDocumentRepository) -> None:
        self._repository = repository

    def upsert_document(self, *, doc_id: str, payload: dict[str, Any]) -> DocumentRecord:
        normalized_payload = dict(payload)
        normalized_payload["doc_id"] = doc_id
        saved_doc_id = self._repository.save(normalized_payload)
        loaded_payload = self._repository.read_document(saved_doc_id)
        return DocumentRecord(doc_id=saved_doc_id, payload=loaded_payload)

    def get_document(self, doc_id: str) -> DocumentRecord:
        try:
            payload = self._repository.read_document(doc_id)
        except KeyError as exc:
            raise DocumentNotFoundError(f"Документ {doc_id} не найден") from exc
        return DocumentRecord(doc_id=doc_id, payload=payload)

    def list_documents(self, *, limit: int = 50, offset: int = 0) -> DocumentListPage:
        rows = self._repository.list_documents(limit=limit, offset=offset)
        items = [
            DocumentRecord(
                doc_id=str(row.get("doc_id", "")),
                payload=dict(row.get("payload") or {}),
                created_at=row.get("created_at"),
                updated_at=row.get("updated_at"),
            )
            for row in rows
        ]
        return DocumentListPage(
            items=items,
            limit=limit,
            offset=offset,
            total_returned=len(items),
        )
