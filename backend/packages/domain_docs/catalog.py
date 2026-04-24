from __future__ import annotations

from typing import Any, Protocol

from domain_docs.templates import TemplateCompiler
from schemas.documents.contracts import TemplateSpec


class TemplateCatalog(Protocol):
    """Catalog boundary for resolving reusable template specs."""

    def get_template_spec(self, template_id: str) -> TemplateSpec | None:
        """Returns a preconfigured TemplateSpec when present."""


class InMemoryTemplateCatalog:
    """Simple in-memory template catalog for template-aware authoring flows."""

    def __init__(self, templates: dict[str, dict[str, Any]] | None = None, *, compiler: TemplateCompiler | None = None) -> None:
        self._templates = dict(templates or {})
        self._compiler = compiler or TemplateCompiler()

    def get_template_spec(self, template_id: str) -> TemplateSpec | None:
        payload = self._templates.get(template_id)
        if payload is None:
            return None
        return self._compiler.compile(template_id=template_id, template_payload=payload)
