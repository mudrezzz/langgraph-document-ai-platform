from __future__ import annotations

from apps.api.dependencies import ApiContainer
from infra.fastmcp.retrieval_service import FastMcpRetrievalService, create_fastmcp_retrieval_server


def create_server() -> object:
    """Создает FastMCP сервер retrieval домена."""

    container = ApiContainer()
    service = FastMcpRetrievalService(container.retrieval_service)
    return create_fastmcp_retrieval_server(service)


def main() -> None:
    server = create_server()

    run_method = getattr(server, "run", None)
    if run_method is None:
        raise RuntimeError("FastMCP server instance не поддерживает метод run()")

    # Запускаем MCP runtime в стандартном режиме FastMCP.
    run_method()


if __name__ == "__main__":
    main()
