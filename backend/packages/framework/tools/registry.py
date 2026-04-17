from __future__ import annotations

from typing import Iterable

from framework.tools.interfaces import ITool


class ToolRegistry:
    """Реестр tool-объектов с простым API регистрации и поиска."""

    def __init__(self) -> None:
        self._tools: dict[str, ITool] = {}

    def register(self, tool: ITool) -> None:
        self._tools[tool.name()] = tool

    def get(self, name: str) -> ITool:
        return self._tools[name]

    def has(self, name: str) -> bool:
        return name in self._tools

    def list_tools(self) -> Iterable[str]:
        return self._tools.keys()
