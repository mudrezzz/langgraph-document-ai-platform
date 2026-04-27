from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ArtifactWriterMcpWriteArtifactInput(BaseModel):
    """Контракт входа MCP tool для записи артефакта."""

    artifact_id: str | None = None
    artifact_type: str = "generic"
    title: str | None = None
    content: str
    format: str = "markdown"
    actor: str | None = None
    roles: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ArtifactWriterMcpWriteArtifactOutput(BaseModel):
    """Контракт ответа MCP tool после записи артефакта."""

    artifact_id: str
    artifact_type: str
    title: str | None = None
    content: str
    format: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class ArtifactWriterMcpGetArtifactInput(BaseModel):
    """Контракт входа MCP tool для чтения артефакта по id."""

    artifact_id: str


class ArtifactWriterMcpGetArtifactOutput(BaseModel):
    """Контракт ответа MCP tool по чтению артефакта."""

    artifact_id: str
    artifact_type: str
    title: str | None = None
    content: str
    format: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class ArtifactWriterMcpListArtifactsInput(BaseModel):
    """Контракт входа MCP tool для списка артефактов."""

    limit: int = Field(default=20, ge=1, le=200)
    offset: int = Field(default=0, ge=0)
    artifact_type: str | None = None


class ArtifactWriterMcpArtifactItem(BaseModel):
    """Элемент списка артефактов в MCP-контуре."""

    artifact_id: str
    artifact_type: str
    title: str | None = None
    format: str
    created_at: datetime | None = None
    updated_at: datetime | None = None


class ArtifactWriterMcpListArtifactsOutput(BaseModel):
    """Контракт ответа MCP tool по списку артефактов."""

    items: list[ArtifactWriterMcpArtifactItem] = Field(default_factory=list)
    limit: int
    offset: int
    total_returned: int
