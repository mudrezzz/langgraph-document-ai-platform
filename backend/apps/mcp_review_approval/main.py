from __future__ import annotations

from apps.api.dependencies import ApiContainer
from infra.fastmcp.review_approval_service import (
    FastMcpReviewApprovalService,
    create_fastmcp_review_approval_server,
)


def create_server() -> object:
    """Создает FastMCP сервер review/approval домена."""

    container = ApiContainer()
    service = FastMcpReviewApprovalService(
        container.authoring_service,
        dispatcher=container.authoring_dispatcher,
    )
    return create_fastmcp_review_approval_server(service)


def main() -> None:
    server = create_server()

    run_method = getattr(server, 'run', None)
    if run_method is None:
        raise RuntimeError('FastMCP server instance не поддерживает метод run()')

    run_method()


if __name__ == '__main__':
    main()
