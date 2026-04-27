from __future__ import annotations

from typing import Any, Callable

from application.document_service import DocumentApplicationService
from application.errors import DocumentNotFoundError
from framework.mcp import BaseFastMcpService
from schemas.mcp.repository import (
    RepositoryMcpDocumentItem,
    RepositoryMcpGetDocumentInput,
    RepositoryMcpGetDocumentOutput,
    RepositoryMcpListDocumentsInput,
    RepositoryMcpListDocumentsOutput,
    RepositoryMcpUpsertDocumentInput,
    RepositoryMcpUpsertDocumentOutput,
)


class FastMcpRepositoryService(BaseFastMcpService):
    """MVP MCP-сервис repository домена с базовыми CRUD tool-ами."""

    def __init__(self, document_service: DocumentApplicationService) -> None:
        super().__init__(service_name="repository-mcp", version="0.1.0")
        self._document_service = document_service
        self._tools: dict[str, Callable[..., Any]] = {}

    def register_tools(self) -> None:
        self._tools = self._register_toolset(
            {
                "upsert_document": self.upsert_document,
                "get_document": self.get_document,
                "list_documents": self.list_documents,
            },
            required_roles={"upsert_document": ("repository_writer",)},
        )

    def upsert_document(self, payload: RepositoryMcpUpsertDocumentInput | dict[str, Any]) -> dict[str, Any]:
        """Создает или обновляет документ в repository."""

        if isinstance(payload, dict):
            validated_payload = RepositoryMcpUpsertDocumentInput.model_validate(payload)
        else:
            validated_payload = payload

        self._authorize_tool(
            "upsert_document",
            actor=validated_payload.actor,
            roles=validated_payload.roles,
        )

        saved = self._document_service.upsert_document(
            doc_id=validated_payload.doc_id,
            payload=validated_payload.payload,
        )
        response = RepositoryMcpUpsertDocumentOutput(doc_id=saved.doc_id, payload=saved.payload)
        return response.model_dump(mode="json")

    def get_document(self, payload: RepositoryMcpGetDocumentInput | dict[str, Any]) -> dict[str, Any]:
        """Читает документ из repository по идентификатору."""

        if isinstance(payload, dict):
            validated_payload = RepositoryMcpGetDocumentInput.model_validate(payload)
        else:
            validated_payload = payload

        try:
            loaded = self._document_service.get_document(validated_payload.doc_id)
        except (DocumentNotFoundError, KeyError) as exc:
            raise self._operation_error(exc) from exc

        response = RepositoryMcpGetDocumentOutput(doc_id=loaded.doc_id, payload=loaded.payload)
        return response.model_dump(mode="json")

    def list_documents(self, payload: RepositoryMcpListDocumentsInput | dict[str, Any] | None = None) -> dict[str, Any]:
        """Возвращает страницу документов из repository."""

        if payload is None:
            validated_payload = RepositoryMcpListDocumentsInput()
        elif isinstance(payload, dict):
            validated_payload = RepositoryMcpListDocumentsInput.model_validate(payload)
        else:
            validated_payload = payload

        page = self._document_service.list_documents(
            limit=validated_payload.limit,
            offset=validated_payload.offset,
        )
        response = RepositoryMcpListDocumentsOutput(
            items=[
                RepositoryMcpDocumentItem(
                    doc_id=item.doc_id,
                    payload=item.payload,
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


def create_fastmcp_repository_server(service: FastMcpRepositoryService) -> Any:
    """Создает FastMCP runtime-сервер для repository service."""

    try:
        from fastmcp import FastMCP
    except Exception as exc:  # pragma: no cover - зависит от внешнего пакета в runtime.
        raise RuntimeError(
            "Не удалось импортировать fastmcp. Установите пакет `fastmcp` для запуска MCP-сервиса."
        ) from exc

    service.register_tools()
    server = FastMCP("repository-mcp")

    @server.tool()
    def upsert_document(doc_id: str, payload: dict, actor: str | None = None, roles: list[str] | None = None) -> dict[str, Any]:
        """MCP tool: upsert_document."""

        return service.upsert_document({"doc_id": doc_id, "payload": payload, "actor": actor, "roles": roles or []})

    @server.tool()
    def get_document(doc_id: str) -> dict[str, Any]:
        """MCP tool: get_document."""

        return service.get_document({"doc_id": doc_id})

    @server.tool()
    def list_documents(limit: int = 20, offset: int = 0) -> dict[str, Any]:
        """MCP tool: list_documents."""

        return service.list_documents({"limit": limit, "offset": offset})

    return server
