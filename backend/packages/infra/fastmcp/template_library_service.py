from __future__ import annotations

from typing import Any, Callable

from application.errors import TemplateNotFoundError
from application.template_library_service import TemplateLibraryApplicationService
from framework.mcp import BaseFastMcpService
from schemas.mcp.template_library import (
    TemplateLibraryMcpGetTemplateInput,
    TemplateLibraryMcpGetTemplateOutput,
    TemplateLibraryMcpListTemplatesInput,
    TemplateLibraryMcpListTemplatesOutput,
    TemplateLibraryMcpTemplateItem,
    TemplateLibraryMcpUpsertTemplateInput,
    TemplateLibraryMcpUpsertTemplateOutput,
)


class FastMcpTemplateLibraryService(BaseFastMcpService):
    """MCP-сервис для управления persisted template library."""

    def __init__(self, template_library_service: TemplateLibraryApplicationService) -> None:
        super().__init__(service_name="template-library-mcp", version="0.1.0")
        self._template_library_service = template_library_service
        self._tools: dict[str, Callable[..., Any]] = {}

    def register_tools(self) -> None:
        self._tools = {
            "upsert_template": self.upsert_template,
            "get_template": self.get_template,
            "list_templates": self.list_templates,
        }

    def metadata(self) -> dict[str, Any]:
        payload = super().metadata()
        payload["tool_names"] = sorted(self._tools.keys())
        return payload

    def upsert_template(self, payload: TemplateLibraryMcpUpsertTemplateInput | dict[str, Any]) -> dict[str, Any]:
        """Создает или обновляет reusable template в template library."""

        validated = TemplateLibraryMcpUpsertTemplateInput.model_validate(payload)
        compiled = self._template_library_service.compile_template(
            template_id=validated.template_id,
            version=validated.version,
            sections=validated.sections,
            validation_rules=validated.validation_rules,
            assembly_rules=validated.assembly_rules,
        )
        self._template_library_service.upsert_template(compiled, metadata=validated.metadata)
        saved = self._template_library_service.get_template(validated.template_id, validated.version)
        response = TemplateLibraryMcpUpsertTemplateOutput(
            template_id=saved.template_id,
            version=saved.version,
            template_spec=saved.template_spec.model_dump(mode="json"),
            metadata=saved.metadata,
            created_at=saved.created_at,
            updated_at=saved.updated_at,
        )
        return response.model_dump(mode="json")

    def get_template(self, payload: TemplateLibraryMcpGetTemplateInput | dict[str, Any]) -> dict[str, Any]:
        """Читает reusable template по идентификатору и опциональной версии."""

        validated = TemplateLibraryMcpGetTemplateInput.model_validate(payload)
        try:
            loaded = self._template_library_service.get_template(validated.template_id, validated.version)
        except (TemplateNotFoundError, KeyError) as exc:
            raise ValueError(str(exc)) from exc

        response = TemplateLibraryMcpGetTemplateOutput(
            template_id=loaded.template_id,
            version=loaded.version,
            template_spec=loaded.template_spec.model_dump(mode="json"),
            metadata=loaded.metadata,
            created_at=loaded.created_at,
            updated_at=loaded.updated_at,
        )
        return response.model_dump(mode="json")

    def list_templates(self, payload: TemplateLibraryMcpListTemplatesInput | dict[str, Any] | None = None) -> dict[str, Any]:
        """Возвращает страницу reusable templates."""

        if payload is None:
            validated = TemplateLibraryMcpListTemplatesInput()
        else:
            validated = TemplateLibraryMcpListTemplatesInput.model_validate(payload)

        page = self._template_library_service.list_templates(
            limit=validated.limit,
            offset=validated.offset,
            template_id=validated.template_id,
        )
        response = TemplateLibraryMcpListTemplatesOutput(
            items=[
                TemplateLibraryMcpTemplateItem(
                    template_id=item.template_id,
                    version=item.version,
                    template_spec=item.template_spec.model_dump(mode="json"),
                    metadata=item.metadata,
                    created_at=item.created_at,
                    updated_at=item.updated_at,
                )
                for item in page.items
            ],
            limit=page.limit,
            offset=page.offset,
            total_returned=page.total_returned,
        )
        return response.model_dump(mode="json")


def create_fastmcp_template_library_server(service: FastMcpTemplateLibraryService) -> Any:
    """Создает FastMCP runtime-сервер для template library service."""

    try:
        from fastmcp import FastMCP
    except Exception as exc:  # pragma: no cover
        raise RuntimeError(
            "Не удалось импортировать fastmcp. Установите пакет `fastmcp` для запуска MCP-сервиса."
        ) from exc

    service.register_tools()
    server = FastMCP("template-library-mcp")

    @server.tool()
    def upsert_template(
        template_id: str,
        version: str = "1",
        sections: list[dict[str, Any]] | None = None,
        validation_rules: list[dict[str, Any]] | None = None,
        assembly_rules: list[dict[str, Any]] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """MCP tool: upsert_template."""

        return service.upsert_template(
            {
                "template_id": template_id,
                "version": version,
                "sections": sections or [],
                "validation_rules": validation_rules or [],
                "assembly_rules": assembly_rules or [],
                "metadata": metadata or {},
            }
        )

    @server.tool()
    def get_template(template_id: str, version: str | None = None) -> dict[str, Any]:
        """MCP tool: get_template."""

        return service.get_template({"template_id": template_id, "version": version})

    @server.tool()
    def list_templates(limit: int = 20, offset: int = 0, template_id: str | None = None) -> dict[str, Any]:
        """MCP tool: list_templates."""

        return service.list_templates({"limit": limit, "offset": offset, "template_id": template_id})

    return server
