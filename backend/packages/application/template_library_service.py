from __future__ import annotations

from datetime import datetime
from typing import Protocol

from pydantic import BaseModel, Field

from application.errors import TemplateNotFoundError
from schemas.documents.contracts import TemplateSpec


class TemplateRecord(BaseModel):
    """Stored template metadata and compiled spec."""

    template_id: str
    version: str
    template_spec: TemplateSpec
    metadata: dict = Field(default_factory=dict)
    created_at: datetime | None = None
    updated_at: datetime | None = None


class TemplateListPage(BaseModel):
    """Read-model page for stored templates."""

    items: list[TemplateRecord] = Field(default_factory=list)
    limit: int
    offset: int
    total_returned: int


class TemplateLibraryStore(Protocol):
    """Persistence port for reusable document templates."""

    def upsert_template(self, template_spec: TemplateSpec, *, metadata: dict | None = None) -> str:
        """Persist a compiled template spec."""

    def get_template(self, template_id: str, version: str | None = None) -> TemplateRecord:
        """Load one template by id/version."""

    def list_templates(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
        template_id: str | None = None,
    ) -> list[TemplateRecord]:
        """List stored templates."""


class TemplateLibraryApplicationService:
    """Application boundary for persisted template library operations."""

    def __init__(self, store: TemplateLibraryStore) -> None:
        self._store = store

    def upsert_template(self, template_spec: TemplateSpec, *, metadata: dict | None = None) -> str:
        return self._store.upsert_template(template_spec, metadata=metadata)

    def get_template(self, template_id: str, version: str | None = None) -> TemplateRecord:
        try:
            return self._store.get_template(template_id, version)
        except KeyError as exc:
            requested = f"{template_id}:{version}" if version else template_id
            raise TemplateNotFoundError(f"Template {requested} не найден") from exc

    def get_template_spec(self, template_id: str, version: str | None = None) -> TemplateSpec:
        return self.get_template(template_id, version).template_spec

    def list_templates(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
        template_id: str | None = None,
    ) -> TemplateListPage:
        items = self._store.list_templates(limit=limit, offset=offset, template_id=template_id)
        return TemplateListPage(
            items=items,
            limit=limit,
            offset=offset,
            total_returned=len(items),
        )


class TemplateLibraryCatalogAdapter:
    """Adapts persisted template library to the existing TemplateCatalog boundary."""

    def __init__(self, template_library_service: TemplateLibraryApplicationService) -> None:
        self._template_library_service = template_library_service

    def get_template_spec(self, template_id: str, version: str | None = None) -> TemplateSpec | None:
        try:
            return self._template_library_service.get_template_spec(template_id, version)
        except TemplateNotFoundError:
            return None
