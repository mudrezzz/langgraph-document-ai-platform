from __future__ import annotations

from apps.api.dependencies import ApiContainer
from infra.fastmcp.template_library_service import (
    FastMcpTemplateLibraryService,
    create_fastmcp_template_library_server,
)


def create_server() -> object:
    """Создает FastMCP сервер template library домена."""

    container = ApiContainer()
    service = FastMcpTemplateLibraryService(container.template_library_service)
    return create_fastmcp_template_library_server(service)


def main() -> None:
    server = create_server()

    run_method = getattr(server, "run", None)
    if run_method is None:
        raise RuntimeError("FastMCP server instance не поддерживает метод run()")

    run_method()


if __name__ == "__main__":
    main()
