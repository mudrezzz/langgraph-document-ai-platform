from __future__ import annotations

from typing import Any, Callable

from application.artifact_service import ArtifactApplicationService
from application.errors import ArtifactNotFoundError
from framework.mcp import BaseFastMcpService
from schemas.mcp.artifact_writer import (
    ArtifactWriterMcpArtifactItem,
    ArtifactWriterMcpGetArtifactInput,
    ArtifactWriterMcpGetArtifactOutput,
    ArtifactWriterMcpListArtifactsInput,
    ArtifactWriterMcpListArtifactsOutput,
    ArtifactWriterMcpWriteArtifactInput,
    ArtifactWriterMcpWriteArtifactOutput,
)


class FastMcpArtifactWriterService(BaseFastMcpService):
    """MVP MCP-сервис записи артефактов."""

    def __init__(self, artifact_service: ArtifactApplicationService) -> None:
        super().__init__(service_name="artifact-writer-mcp", version="0.1.0")
        self._artifact_service = artifact_service
        self._tools: dict[str, Callable[..., Any]] = {}

    def register_tools(self) -> None:
        self._tools = self._register_toolset(
            {
                "write_artifact": self.write_artifact,
                "get_artifact": self.get_artifact,
                "list_artifacts": self.list_artifacts,
            },
            required_roles={"write_artifact": ("artifact_writer",)},
        )

    def write_artifact(self, payload: ArtifactWriterMcpWriteArtifactInput | dict[str, Any]) -> dict[str, Any]:
        """Создает или обновляет артефакт в artifact store."""

        if isinstance(payload, dict):
            validated_payload = ArtifactWriterMcpWriteArtifactInput.model_validate(payload)
        else:
            validated_payload = payload

        self._authorize_tool(
            "write_artifact",
            actor=validated_payload.actor,
            roles=validated_payload.roles,
        )

        saved = self._artifact_service.write_artifact(
            artifact_id=validated_payload.artifact_id,
            artifact_type=validated_payload.artifact_type,
            payload={
                "title": validated_payload.title,
                "content": validated_payload.content,
                "format": validated_payload.format,
                "metadata": validated_payload.metadata,
            },
        )
        saved_payload = saved.payload
        response = ArtifactWriterMcpWriteArtifactOutput(
            artifact_id=saved.artifact_id,
            artifact_type=saved.artifact_type,
            title=saved_payload.get("title"),
            content=str(saved_payload.get("content", "")),
            format=str(saved_payload.get("format", "markdown")),
            metadata=dict(saved_payload.get("metadata") or {}),
        )
        return response.model_dump(mode="json")

    def get_artifact(self, payload: ArtifactWriterMcpGetArtifactInput | dict[str, Any]) -> dict[str, Any]:
        """Читает артефакт по идентификатору."""

        if isinstance(payload, dict):
            validated_payload = ArtifactWriterMcpGetArtifactInput.model_validate(payload)
        else:
            validated_payload = payload

        try:
            loaded = self._artifact_service.get_artifact(validated_payload.artifact_id)
        except (ArtifactNotFoundError, KeyError) as exc:
            raise self._operation_error(exc) from exc

        loaded_payload = loaded.payload
        response = ArtifactWriterMcpGetArtifactOutput(
            artifact_id=loaded.artifact_id,
            artifact_type=loaded.artifact_type,
            title=loaded_payload.get("title"),
            content=str(loaded_payload.get("content", "")),
            format=str(loaded_payload.get("format", "markdown")),
            metadata=dict(loaded_payload.get("metadata") or {}),
        )
        return response.model_dump(mode="json")

    def list_artifacts(
        self,
        payload: ArtifactWriterMcpListArtifactsInput | dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Возвращает страницу артефактов."""

        if payload is None:
            validated_payload = ArtifactWriterMcpListArtifactsInput()
        elif isinstance(payload, dict):
            validated_payload = ArtifactWriterMcpListArtifactsInput.model_validate(payload)
        else:
            validated_payload = payload

        page = self._artifact_service.list_artifacts(
            limit=validated_payload.limit,
            offset=validated_payload.offset,
            artifact_type=validated_payload.artifact_type,
        )
        response = ArtifactWriterMcpListArtifactsOutput(
            items=[
                ArtifactWriterMcpArtifactItem(
                    artifact_id=item.artifact_id,
                    artifact_type=item.artifact_type,
                    title=item.payload.get("title"),
                    format=str(item.payload.get("format", "markdown")),
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


def create_fastmcp_artifact_writer_server(service: FastMcpArtifactWriterService) -> Any:
    """Создает FastMCP runtime-сервер для artifact writer service."""

    try:
        from fastmcp import FastMCP
    except Exception as exc:  # pragma: no cover - зависит от внешнего пакета в runtime.
        raise RuntimeError(
            "Не удалось импортировать fastmcp. Установите пакет `fastmcp` для запуска MCP-сервиса."
        ) from exc

    service.register_tools()
    server = FastMCP("artifact-writer-mcp")

    @server.tool()
    def write_artifact(
        content: str,
        artifact_type: str = "generic",
        artifact_id: str | None = None,
        title: str | None = None,
        format: str = "markdown",
        actor: str | None = None,
        roles: list[str] | None = None,
        metadata: dict | None = None,
    ) -> dict[str, Any]:
        """MCP tool: write_artifact."""

        return service.write_artifact(
            {
                "artifact_id": artifact_id,
                "artifact_type": artifact_type,
                "title": title,
                "content": content,
                "format": format,
                "actor": actor,
                "roles": roles or [],
                "metadata": metadata or {},
            }
        )

    @server.tool()
    def get_artifact(artifact_id: str) -> dict[str, Any]:
        """MCP tool: get_artifact."""

        return service.get_artifact({"artifact_id": artifact_id})

    @server.tool()
    def list_artifacts(limit: int = 20, offset: int = 0, artifact_type: str | None = None) -> dict[str, Any]:
        """MCP tool: list_artifacts."""

        return service.list_artifacts(
            {
                "limit": limit,
                "offset": offset,
                "artifact_type": artifact_type,
            }
        )

    return server
