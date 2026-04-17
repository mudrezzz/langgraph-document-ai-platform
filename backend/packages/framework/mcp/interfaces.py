from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class IMcpService(Protocol):
    """Контракт MCP-сервиса."""

    def register_tools(self) -> None:
        """Регистрирует MCP-инструменты сервиса."""

    def metadata(self) -> dict[str, Any]:
        """Возвращает метаданные MCP-сервиса."""


class McpToolAdapter:
    """Адаптер между framework tools и MCP tools."""

    def to_mcp_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        return payload
