from __future__ import annotations

from abc import ABC, abstractmethod

from pydantic import BaseModel

from framework.tools.interfaces import ITool, ToolContext


class BaseTool(ABC, ITool):
    """База для инструментов с валидацией входа и единым контрактом выхода."""

    @abstractmethod
    def name(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def description(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def input_schema(self) -> type[BaseModel]:
        raise NotImplementedError

    @abstractmethod
    def output_schema(self) -> type[BaseModel]:
        raise NotImplementedError

    def execute(self, command: BaseModel, context: ToolContext) -> BaseModel:
        # Проверяем, что команда соответствует ожидаемой схеме.
        validated_command = self.input_schema().model_validate(command)
        result = self._run(validated_command, context)
        return self.output_schema().model_validate(result)

    @abstractmethod
    def _run(self, command: BaseModel, context: ToolContext) -> BaseModel | dict:
        """Содержит прикладную реализацию конкретного инструмента."""
