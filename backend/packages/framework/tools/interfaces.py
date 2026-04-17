from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, Field


class ToolContext(BaseModel):
    """Контекст вызова инструмента."""

    task_id: str
    actor: str
    metadata: dict[str, Any] = Field(default_factory=dict)


@runtime_checkable
class ITool(Protocol):
    """Базовый контракт tool-объекта."""

    def name(self) -> str:
        """Возвращает уникальное имя инструмента."""

    def description(self) -> str:
        """Возвращает краткое описание назначения инструмента."""

    def input_schema(self) -> type[BaseModel]:
        """Возвращает Pydantic-схему входа."""

    def output_schema(self) -> type[BaseModel]:
        """Возвращает Pydantic-схему выхода."""

    def execute(self, command: BaseModel, context: ToolContext) -> BaseModel:
        """Выполняет полезное действие инструмента."""
