from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


TemplateLifecycleStatus = Literal["draft", "published", "deprecated", "archived"]


class TemplateLibraryMcpUpsertTemplateInput(BaseModel):
    """Контракт входа MCP tool для upsert reusable template."""

    template_id: str
    version: str = "1"
    status: TemplateLifecycleStatus = "draft"
    actor: str | None = None
    roles: list[str] = Field(default_factory=list)
    sections: list[dict[str, Any]] = Field(default_factory=list)
    validation_rules: list[dict[str, Any]] = Field(default_factory=list)
    assembly_rules: list[dict[str, Any]] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class TemplateLibraryMcpTemplateItem(BaseModel):
    """Элемент reusable template в MCP-контуре."""

    template_id: str
    version: str
    status: TemplateLifecycleStatus = "draft"
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
    status: TemplateLifecycleStatus | None = None


class TemplateLibraryMcpPublishTemplateInput(BaseModel):
    """Контракт входа MCP tool для публикации версии reusable template."""

    template_id: str
    version: str
    actor: str | None = None
    roles: list[str] = Field(default_factory=list)


class TemplateLibraryMcpPublishTemplateOutput(TemplateLibraryMcpTemplateItem):
    """Контракт ответа MCP tool после публикации reusable template."""


class TemplateLibraryMcpSetTemplateStatusInput(BaseModel):
    """Контракт входа MCP tool для lifecycle transition reusable template."""

    template_id: str
    version: str
    status: TemplateLifecycleStatus
    reason: str | None = None
    actor: str | None = None
    roles: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class TemplateLibraryMcpSetTemplateStatusOutput(TemplateLibraryMcpTemplateItem):
    """Контракт ответа MCP tool после lifecycle transition reusable template."""


class TemplateLibraryMcpListTemplatesOutput(BaseModel):
    """Контракт ответа MCP tool по list reusable templates."""

    items: list[TemplateLibraryMcpTemplateItem] = Field(default_factory=list)
    limit: int
    offset: int
    total_returned: int
