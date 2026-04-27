from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class RepositoryMcpUpsertDocumentInput(BaseModel):
    """Контракт входа MCP tool для upsert документа."""

    doc_id: str
    actor: str | None = None
    roles: list[str] = Field(default_factory=list)
    payload: dict[str, Any] = Field(default_factory=dict)


class RepositoryMcpUpsertDocumentOutput(BaseModel):
    """Контракт ответа MCP tool после upsert документа."""

    doc_id: str
    payload: dict[str, Any] = Field(default_factory=dict)


class RepositoryMcpGetDocumentInput(BaseModel):
    """Контракт входа MCP tool для чтения документа по id."""

    doc_id: str


class RepositoryMcpGetDocumentOutput(BaseModel):
    """Контракт ответа MCP tool по чтению документа."""

    doc_id: str
    payload: dict[str, Any] = Field(default_factory=dict)


class RepositoryMcpListDocumentsInput(BaseModel):
    """Контракт входа MCP tool для list документов."""

    limit: int = Field(default=20, ge=1, le=200)
    offset: int = Field(default=0, ge=0)


class RepositoryMcpDocumentItem(BaseModel):
    """Элемент списка документов в MCP-контуре."""

    doc_id: str
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime | None = None
    updated_at: datetime | None = None


class RepositoryMcpListDocumentsOutput(BaseModel):
    """Контракт ответа MCP tool по list документов."""

    items: list[RepositoryMcpDocumentItem] = Field(default_factory=list)
    limit: int
    offset: int
    total_returned: int
