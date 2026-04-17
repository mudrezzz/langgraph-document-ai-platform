from __future__ import annotations

from typing import Any

from framework.mcp.interfaces import IMcpService


class BaseFastMcpService(IMcpService):
    """Базовая реализация MCP-сервиса на FastMCP (скелет)."""

    def __init__(self, service_name: str, version: str = "0.1.0") -> None:
        self._service_name = service_name
        self._version = version

    def register_tools(self) -> None:
        # Реальная регистрация будет добавлена после подключения FastMCP.
        return None

    def metadata(self) -> dict[str, Any]:
        return {"service_name": self._service_name, "version": self._version}