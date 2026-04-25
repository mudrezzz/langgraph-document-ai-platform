from __future__ import annotations

from datetime import datetime
from typing import Literal, Protocol

from pydantic import BaseModel, Field

from application.errors import InvalidTemplateStatusTransitionError, TemplateNotFoundError
from domain_docs import TemplateCompiler
from schemas.documents.contracts import TemplateSpec

TemplateStatus = Literal["draft", "published", "deprecated", "archived"]

_ALLOWED_TEMPLATE_STATUSES = {"draft", "published", "deprecated", "archived"}
_ALLOWED_TEMPLATE_TRANSITIONS: dict[str, set[str]] = {
    "draft": {"draft", "published", "deprecated", "archived"},
    "published": {"published", "draft", "deprecated", "archived"},
    "deprecated": {"deprecated", "draft", "published", "archived"},
    "archived": {"archived"},
}


class TemplateRecord(BaseModel):
    """Stored template metadata and compiled spec."""

    template_id: str
    version: str
    status: TemplateStatus = "draft"
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

    def upsert_template(
        self,
        template_spec: TemplateSpec,
        *,
        metadata: dict | None = None,
        status: TemplateStatus | None = None,
    ) -> str:
        """Persist a compiled template spec."""

    def get_template(
        self,
        template_id: str,
        version: str | None = None,
        *,
        published_only: bool = False,
        allow_archived: bool = True,
    ) -> TemplateRecord:
        """Load one template by id/version."""

    def publish_template(self, template_id: str, version: str) -> TemplateRecord:
        """Mark one template version as published."""

    def set_template_status(
        self,
        template_id: str,
        version: str,
        status: TemplateStatus,
        *,
        reason: str | None = None,
        actor: str | None = None,
        metadata: dict | None = None,
    ) -> TemplateRecord:
        """Apply lifecycle transition to one template version."""

    def list_templates(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
        template_id: str | None = None,
        status: TemplateStatus | None = None,
    ) -> list[TemplateRecord]:
        """List stored templates."""


class TemplateLibraryApplicationService:
    """Application boundary for persisted template library operations."""

    def __init__(self, store: TemplateLibraryStore, *, template_compiler: TemplateCompiler | None = None) -> None:
        self._store = store
        self._template_compiler = template_compiler or TemplateCompiler()

    def compile_template(
        self,
        *,
        template_id: str,
        version: str = "1",
        sections: list[dict] | None = None,
        validation_rules: list[dict] | None = None,
        assembly_rules: list[dict] | None = None,
    ) -> TemplateSpec:
        return self._template_compiler.compile(
            template_id=template_id,
            template_payload={
                "version": version,
                "sections": list(sections or []),
                "validation_rules": list(validation_rules or []),
                "assembly_rules": list(assembly_rules or []),
            },
        )

    def upsert_template(
        self,
        template_spec: TemplateSpec,
        *,
        metadata: dict | None = None,
        status: TemplateStatus | None = None,
    ) -> str:
        existing: TemplateRecord | None = None
        try:
            existing = self._store.get_template(template_spec.template_id, template_spec.version)
        except KeyError:
            existing = None

        requested_status = _normalize_template_status(status) if status is not None else None
        persisted_status = existing.status if existing is not None else None
        initial_status = persisted_status or "draft"
        saved_template_id = self._store.upsert_template(
            template_spec,
            metadata=metadata,
            status=initial_status,
        )
        if requested_status is not None and requested_status != initial_status:
            self.set_template_status(
                template_spec.template_id,
                template_spec.version,
                requested_status,
                reason="upsert_requested_status",
                actor="template-library-service",
            )
        return saved_template_id

    def get_template(
        self,
        template_id: str,
        version: str | None = None,
        *,
        published_only: bool = False,
        allow_archived: bool = True,
    ) -> TemplateRecord:
        try:
            return self._store.get_template(
                template_id,
                version,
                published_only=published_only,
                allow_archived=allow_archived,
            )
        except KeyError as exc:
            requested = f"{template_id}:{version}" if version else template_id
            if published_only and version is None:
                requested = f"published template {template_id}"
            elif version is not None and not allow_archived:
                requested = f"active template {template_id}:{version}"
            raise TemplateNotFoundError(f"Template {requested} не найден") from exc

    def publish_template(self, template_id: str, version: str) -> TemplateRecord:
        return self.set_template_status(template_id, version, "published")

    def set_template_status(
        self,
        template_id: str,
        version: str,
        status: TemplateStatus,
        *,
        reason: str | None = None,
        actor: str | None = None,
        metadata: dict | None = None,
    ) -> TemplateRecord:
        resolved_status = _normalize_template_status(status)
        try:
            current = self._store.get_template(template_id, version)
        except KeyError as exc:
            raise TemplateNotFoundError(f"Template {template_id}:{version} не найден") from exc

        _validate_template_status_transition(current.status, resolved_status)
        try:
            return self._store.set_template_status(
                template_id,
                version,
                resolved_status,
                reason=reason,
                actor=actor,
                metadata=metadata,
            )
        except KeyError as exc:
            raise TemplateNotFoundError(f"Template {template_id}:{version} не найден") from exc

    def get_template_spec(
        self,
        template_id: str,
        version: str | None = None,
        *,
        published_only: bool = False,
        allow_archived: bool = True,
    ) -> TemplateSpec:
        return self.get_template(
            template_id,
            version,
            published_only=published_only,
            allow_archived=allow_archived,
        ).template_spec

    def list_templates(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
        template_id: str | None = None,
        status: TemplateStatus | None = None,
    ) -> TemplateListPage:
        resolved_status = _normalize_template_status(status) if status is not None else None
        items = self._store.list_templates(limit=limit, offset=offset, template_id=template_id, status=resolved_status)
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
        if version is None:
            try:
                return self._template_library_service.get_template_spec(
                    template_id,
                    published_only=True,
                    allow_archived=False,
                )
            except TemplateNotFoundError:
                page = self._template_library_service.list_templates(limit=1, offset=0, template_id=template_id)
                if page.total_returned > 0:
                    raise TemplateNotFoundError(
                        f"Template {template_id} не имеет published version для authoring"
                    )
                return None

        try:
            record = self._template_library_service.get_template(template_id, version)
        except TemplateNotFoundError:
            return None
        if record.status == "archived":
            raise TemplateNotFoundError(f"Template {template_id}:{version} archived и недоступен для authoring")
        return record.template_spec


def _normalize_template_status(status: str) -> TemplateStatus:
    normalized = str(status).strip().lower()
    if normalized not in _ALLOWED_TEMPLATE_STATUSES:
        raise ValueError("status должен быть draft, published, deprecated или archived")
    return normalized  # type: ignore[return-value]


def _validate_template_status_transition(current_status: TemplateStatus, next_status: TemplateStatus) -> None:
    if next_status not in _ALLOWED_TEMPLATE_TRANSITIONS[current_status]:
        raise InvalidTemplateStatusTransitionError(
            f"Переход статуса template {current_status} -> {next_status} не разрешен"
        )
