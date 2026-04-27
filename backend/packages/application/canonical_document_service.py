from __future__ import annotations

from datetime import datetime
from typing import Protocol

from pydantic import BaseModel, Field

from application.errors import DocumentNotFoundError
from schemas.documents.contracts import CanonicalDocument


class KnowledgeBlockRecord(BaseModel):
    """Read-model record for one canonical knowledge block."""

    block_ref: str
    doc_id: str
    version: str
    block_id: str
    block_type: str
    text: str
    heading_path: list[str] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)
    is_latest: bool = True
    created_at: datetime | None = None
    updated_at: datetime | None = None


class CanonicalDocumentVersionRecord(BaseModel):
    """Read-model record for one persisted canonical document version."""

    doc_id: str
    version: str
    source_path: str
    file_type: str
    metadata_profile: dict = Field(default_factory=dict)
    is_latest: bool = False
    created_at: datetime | None = None
    updated_at: datetime | None = None


class CanonicalDocumentListPage(BaseModel):
    """Read-model page for canonical documents."""

    items: list[CanonicalDocument] = Field(default_factory=list)
    limit: int
    offset: int
    total_returned: int


class CanonicalDocumentVersionListPage(BaseModel):
    """Read-model page for canonical document versions."""

    items: list[CanonicalDocumentVersionRecord] = Field(default_factory=list)
    limit: int
    offset: int
    total_returned: int


class KnowledgeBlockListPage(BaseModel):
    """Read-model page for canonical knowledge blocks."""

    items: list[KnowledgeBlockRecord] = Field(default_factory=list)
    limit: int
    offset: int
    total_returned: int


class CanonicalDocumentStore(Protocol):
    """Persistence port for canonical documents and derived blocks."""

    def save_document(self, document: CanonicalDocument) -> str:
        """Persist a canonical document and its content blocks."""

    def get_document(self, doc_id: str, version: str | None = None) -> CanonicalDocument:
        """Load a canonical document by id and optional explicit version."""

    def list_documents(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
        file_type: str | None = None,
    ) -> list[CanonicalDocument]:
        """List canonical documents using latest-version policy."""

    def list_versions(
        self,
        doc_id: str,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> list[CanonicalDocumentVersionRecord]:
        """List persisted versions for one canonical document identity."""

    def list_blocks(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
        doc_id: str | None = None,
        version: str | None = None,
        block_type: str | None = None,
    ) -> list[KnowledgeBlockRecord]:
        """List derived knowledge blocks using latest-version policy by default."""


class CanonicalDocumentApplicationService:
    """Application boundary for canonical document read/write operations."""

    def __init__(self, store: CanonicalDocumentStore) -> None:
        self._store = store

    def save_document(self, document: CanonicalDocument) -> str:
        return self._store.save_document(document)

    def get_document(self, doc_id: str, version: str | None = None) -> CanonicalDocument:
        try:
            return self._store.get_document(doc_id, version=version)
        except KeyError as exc:
            suffix = f"@{version}" if version else ""
            raise DocumentNotFoundError(f"Canonical document {doc_id}{suffix} не найден") from exc

    def list_documents(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
        file_type: str | None = None,
    ) -> CanonicalDocumentListPage:
        items = self._store.list_documents(limit=limit, offset=offset, file_type=file_type)
        return CanonicalDocumentListPage(
            items=items,
            limit=limit,
            offset=offset,
            total_returned=len(items),
        )

    def list_versions(
        self,
        doc_id: str,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> CanonicalDocumentVersionListPage:
        items = self._store.list_versions(doc_id, limit=limit, offset=offset)
        return CanonicalDocumentVersionListPage(
            items=items,
            limit=limit,
            offset=offset,
            total_returned=len(items),
        )

    def list_blocks(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
        doc_id: str | None = None,
        version: str | None = None,
        block_type: str | None = None,
    ) -> KnowledgeBlockListPage:
        items = self._store.list_blocks(
            limit=limit,
            offset=offset,
            doc_id=doc_id,
            version=version,
            block_type=block_type,
        )
        return KnowledgeBlockListPage(
            items=items,
            limit=limit,
            offset=offset,
            total_returned=len(items),
        )
