from __future__ import annotations

from typing import Any, Callable

from application.errors import InvalidTemplateStatusTransitionError, TemplateNotFoundError
from application.template_library_service import TemplateLibraryApplicationService
from framework.mcp import BaseFastMcpService
from schemas.mcp.template_library import (
    TemplateLibraryMcpGetTemplateInput,
    TemplateLibraryMcpGetTemplateOutput,
    TemplateLibraryMcpListTemplatesInput,
    TemplateLibraryMcpListTemplatesOutput,
    TemplateLibraryMcpPublishTemplateInput,
    TemplateLibraryMcpPublishTemplateOutput,
    TemplateLibraryMcpSetTemplateStatusInput,
    TemplateLibraryMcpSetTemplateStatusOutput,
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
        self._tools = self._register_toolset(
            {
                "upsert_template": self.upsert_template,
                "publish_template": self.publish_template,
                "set_template_status": self.set_template_status,
                "get_template": self.get_template,
                "list_templates": self.list_templates,
            }
        )

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
        self._template_library_service.upsert_template(
            compiled,
            metadata=validated.metadata,
            status=validated.status,
        )
        saved = self._template_library_service.get_template(validated.template_id, validated.version)
        response = TemplateLibraryMcpUpsertTemplateOutput(
            template_id=saved.template_id,
            version=saved.version,
            status=saved.status,
            template_spec=saved.template_spec.model_dump(mode="json"),
            metadata=saved.metadata,
            created_at=saved.created_at,
            updated_at=saved.updated_at,
        )
        return response.model_dump(mode="json")

    def publish_template(self, payload: TemplateLibraryMcpPublishTemplateInput | dict[str, Any]) -> dict[str, Any]:
        """Публикует конкретную version reusable template."""

        validated = TemplateLibraryMcpPublishTemplateInput.model_validate(payload)
        try:
            published = self._template_library_service.publish_template(validated.template_id, validated.version)
        except (TemplateNotFoundError, InvalidTemplateStatusTransitionError) as exc:
            raise self._operation_error(exc) from exc

        response = TemplateLibraryMcpPublishTemplateOutput(
            template_id=published.template_id,
            version=published.version,
            status=published.status,
            template_spec=published.template_spec.model_dump(mode="json"),
            metadata=published.metadata,
            created_at=published.created_at,
            updated_at=published.updated_at,
        )
        return response.model_dump(mode="json")

    def set_template_status(self, payload: TemplateLibraryMcpSetTemplateStatusInput | dict[str, Any]) -> dict[str, Any]:
        """Применяет lifecycle transition к reusable template."""

        validated = TemplateLibraryMcpSetTemplateStatusInput.model_validate(payload)
        try:
            updated = self._template_library_service.set_template_status(
                validated.template_id,
                validated.version,
                validated.status,
                reason=validated.reason,
                actor=validated.actor,
                metadata=validated.metadata,
            )
        except (TemplateNotFoundError, InvalidTemplateStatusTransitionError) as exc:
            raise self._operation_error(exc) from exc

        response = TemplateLibraryMcpSetTemplateStatusOutput(
            template_id=updated.template_id,
            version=updated.version,
            status=updated.status,
            template_spec=updated.template_spec.model_dump(mode="json"),
            metadata=updated.metadata,
            created_at=updated.created_at,
            updated_at=updated.updated_at,
        )
        return response.model_dump(mode="json")

    def get_template(self, payload: TemplateLibraryMcpGetTemplateInput | dict[str, Any]) -> dict[str, Any]:
        """Читает reusable template по идентификатору и опциональной версии."""

        validated = TemplateLibraryMcpGetTemplateInput.model_validate(payload)
        try:
            loaded = self._template_library_service.get_template(validated.template_id, validated.version)
        except (TemplateNotFoundError, KeyError) as exc:
            raise self._operation_error(exc) from exc

        response = TemplateLibraryMcpGetTemplateOutput(
            template_id=loaded.template_id,
            version=loaded.version,
            status=loaded.status,
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
            status=validated.status,
        )
        response = TemplateLibraryMcpListTemplatesOutput(
            items=[
                TemplateLibraryMcpTemplateItem(
                    template_id=item.template_id,
                    version=item.version,
                    status=item.status,
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
        status: str = "draft",
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
                "status": status,
                "sections": sections or [],
                "validation_rules": validation_rules or [],
                "assembly_rules": assembly_rules or [],
                "metadata": metadata or {},
            }
        )

    @server.tool()
    def publish_template(template_id: str, version: str) -> dict[str, Any]:
        """MCP tool: publish_template."""

        return service.publish_template({"template_id": template_id, "version": version})

    @server.tool()
    def set_template_status(
        template_id: str,
        version: str,
        status: str,
        reason: str | None = None,
        actor: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """MCP tool: set_template_status."""

        return service.set_template_status(
            {
                "template_id": template_id,
                "version": version,
                "status": status,
                "reason": reason,
                "actor": actor,
                "metadata": metadata or {},
            }
        )

    @server.tool()
    def get_template(template_id: str, version: str | None = None) -> dict[str, Any]:
        """MCP tool: get_template."""

        return service.get_template({"template_id": template_id, "version": version})

    @server.tool()
    def list_templates(
        limit: int = 20,
        offset: int = 0,
        template_id: str | None = None,
        status: str | None = None,
    ) -> dict[str, Any]:
        """MCP tool: list_templates."""

        return service.list_templates(
            {"limit": limit, "offset": offset, "template_id": template_id, "status": status}
        )

    return server
