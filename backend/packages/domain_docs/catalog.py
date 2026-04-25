from __future__ import annotations

from typing import Any, Protocol

from domain_docs.templates import TemplateCompiler
from schemas.documents.contracts import TemplateSpec


class TemplateCatalog(Protocol):
    """Catalog boundary for resolving reusable template specs."""

    def get_template_spec(self, template_id: str, version: str | None = None) -> TemplateSpec | None:
        """Returns a preconfigured TemplateSpec when present."""


class InMemoryTemplateCatalog:
    """Simple in-memory template catalog for template-aware authoring flows."""

    def __init__(self, templates: dict[str, dict[str, Any]] | dict[tuple[str, str], dict[str, Any]] | None = None, *, compiler: TemplateCompiler | None = None) -> None:
        self._templates = dict(templates or {})
        self._compiler = compiler or TemplateCompiler()

    def get_template_spec(self, template_id: str, version: str | None = None) -> TemplateSpec | None:
        payload = self._resolve_payload(template_id=template_id, version=version)
        if payload is None:
            return None
        resolved_version = version or str(payload.get("version", "1"))
        compiled = self._compiler.compile(template_id=template_id, template_payload=payload)
        if compiled.version != resolved_version:
            return compiled.model_copy(update={"version": resolved_version})
        return compiled

    def _resolve_payload(self, *, template_id: str, version: str | None) -> dict[str, Any] | None:
        if version is not None:
            payload = self._templates.get((template_id, version))
            if isinstance(payload, dict):
                return dict(payload)

        payload = self._templates.get(template_id)
        if isinstance(payload, dict):
            return dict(payload)

        versioned: list[tuple[str, dict[str, Any]]] = []
        for key, value in self._templates.items():
            if not isinstance(key, tuple) or len(key) != 2 or key[0] != template_id or not isinstance(value, dict):
                continue
            versioned.append((str(key[1]), dict(value)))
        if not versioned:
            return None
        versioned.sort(key=lambda item: item[0], reverse=True)
        return versioned[0][1]
