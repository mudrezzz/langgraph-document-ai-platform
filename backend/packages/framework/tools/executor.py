from __future__ import annotations

from pydantic import BaseModel

from framework.tools.interfaces import ToolContext
from framework.tools.registry import ToolRegistry


class ToolExecutor:
    """Унифицированный исполнитель инструментов."""

    def __init__(self, registry: ToolRegistry) -> None:
        self._registry = registry

    def execute(self, tool_name: str, command: BaseModel, context: ToolContext) -> BaseModel:
        # Централизуем lookup инструмента, чтобы не дублировать эту логику в агентах.
        tool = self._registry.get(tool_name)
        return tool.execute(command, context)
