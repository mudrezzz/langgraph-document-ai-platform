from __future__ import annotations

from typing import Any, Callable

from application.retrieval_service import RetrievalApplicationService
from framework.mcp import BaseFastMcpService
from schemas.api.contracts import StartRetrievalTaskRequest
from schemas.mcp.retrieval import (
    RetrievalMcpBuildEvidencePackInput,
    RetrievalMcpBuildEvidencePackOutput,
)
from schemas.rag.contracts import RetrievalFilter


class FastMcpRetrievalService(BaseFastMcpService):
    """MVP MCP-сервис retrieval домена с минимальным набором tool-ов."""

    def __init__(self, retrieval_service: RetrievalApplicationService) -> None:
        super().__init__(service_name="retrieval-mcp", version="0.1.0")
        self._retrieval_service = retrieval_service
        self._tools: dict[str, Callable[..., Any]] = {}

    def register_tools(self) -> None:
        # На первом шаге фиксируем минимальный рабочий tool для end-to-end retrieval вызова.
        self._tools = {"build_evidence_pack": self.build_evidence_pack}

    def metadata(self) -> dict[str, Any]:
        payload = super().metadata()
        payload["tool_names"] = sorted(self._tools.keys())
        return payload

    def build_evidence_pack(self, payload: RetrievalMcpBuildEvidencePackInput | dict[str, Any]) -> dict[str, Any]:
        """Запускает retrieval задачу и сразу возвращает собранный evidence pack."""

        if isinstance(payload, dict):
            validated_payload = RetrievalMcpBuildEvidencePackInput.model_validate(payload)
        else:
            validated_payload = payload

        request = StartRetrievalTaskRequest(
            query=validated_payload.query,
            filters=RetrievalFilter(
                project_id=validated_payload.project_id,
                document_types=validated_payload.document_types,
            ),
            task_context=validated_payload.task_context,
        )

        started = self._retrieval_service.start(request)
        status = self._retrieval_service.status(started.task_id)
        evidence = self._retrieval_service.evidence(started.task_id)

        response = RetrievalMcpBuildEvidencePackOutput(
            task_id=started.task_id,
            status=status.status,
            details=status.details,
            evidence_pack=evidence.evidence_pack,
        )
        return response.model_dump(mode="json")


def create_fastmcp_retrieval_server(service: FastMcpRetrievalService) -> Any:
    """Создает FastMCP runtime-сервер для retrieval service.

    Импорт FastMCP выполняется лениво, чтобы backend-контур не зависел от пакета,
    если MCP-сервис не запускается в текущем окружении.
    """

    try:
        from fastmcp import FastMCP
    except Exception as exc:  # pragma: no cover - зависит от внешнего пакета в runtime.
        raise RuntimeError(
            "Не удалось импортировать fastmcp. Установите пакет `fastmcp` для запуска MCP-сервиса."
        ) from exc

    service.register_tools()
    server = FastMCP("retrieval-mcp")

    @server.tool()
    def build_evidence_pack(
        query: str,
        project_id: str = "p1",
        document_types: list[str] | None = None,
        task_context: dict | None = None,
    ) -> dict[str, Any]:
        """MCP tool: build_evidence_pack."""

        payload = RetrievalMcpBuildEvidencePackInput(
            query=query,
            project_id=project_id,
            document_types=document_types or [
                "requirements",
                "methodology",
                "security",
                "operations",
                "governance",
            ],
            task_context=task_context or {},
        )
        return service.build_evidence_pack(payload)

    return server
