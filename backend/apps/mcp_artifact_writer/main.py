from __future__ import annotations

from apps.api.dependencies import ApiContainer
from infra.fastmcp.artifact_writer_service import (
    FastMcpArtifactWriterService,
    create_fastmcp_artifact_writer_server,
)


def create_server() -> object:
    """Создает FastMCP сервер artifact writer домена."""

    container = ApiContainer()
    service = FastMcpArtifactWriterService(container.artifact_service)
    return create_fastmcp_artifact_writer_server(service)


def main() -> None:
    server = create_server()

    run_method = getattr(server, "run", None)
    if run_method is None:
        raise RuntimeError("FastMCP server instance не поддерживает метод run()")

    # Запускаем MCP runtime в стандартном режиме FastMCP.
    run_method()


if __name__ == "__main__":
    main()
