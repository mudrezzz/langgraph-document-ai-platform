from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class TemplateLibraryMcpUpsertTemplateInput(BaseModel):
    """Контракт входа MCP tool для upsert reusable template."""

    template_id: str
    version: str = "1"
    sections: list[dict[str, Any]] = Field(default_factory=list)
    validation_rules: list[dict[str, Any]] = Field(default_factory=list)
    assembly_rules: list[dict[str, Any]] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class TemplateLibraryMcpTemplateItem(BaseModel):
    """Элемент reusable template в MCP-контуре."""

    template_id: str
    version: str
    template_spec: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime | None = None
    updated_at: datetime | None = None


class TemplateLibraryMcpUpsertTemplateOutput(TemplateLibraryMcpTemplateItem):
    """Контракт ответа MCP tool после upsert reusable template."""


class TemplateLibraryMcpGetTemplateInput(BaseModel):
    """Контракт входа MCP tool для чтения шаблона по id/version."""

    template_id: str
    version: str | None = None


class TemplateLibraryMcpGetTemplateOutput(TemplateLibraryMcpTemplateItem):
    """Контракт ответа MCP tool по чтению reusable template."""


class TemplateLibraryMcpListTemplatesInput(BaseModel):
    """Контракт входа MCP tool для list reusable templates."""

    limit: int = Field(default=20, ge=1, le=200)
    offset: int = Field(default=0, ge=0)
    template_id: str | None = None


class TemplateLibraryMcpListTemplatesOutput(BaseModel):
    """Контракт ответа MCP tool по list reusable templates."""

    items: list[TemplateLibraryMcpTemplateItem] = Field(default_factory=list)
    limit: int
    offset: int
    total_returned: int
