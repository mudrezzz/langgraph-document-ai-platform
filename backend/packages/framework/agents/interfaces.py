from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, Field


class AgentContext(BaseModel):
    """Контекст исполнения агента в рамках workflow."""

    task_id: str
    node_name: str
    correlation_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class AgentResult(BaseModel):
    """Нормализованный результат вызова агента."""

    raw_output: Any
    metadata: dict[str, Any] = Field(default_factory=dict)


@runtime_checkable
class IAgent(Protocol):
    """Базовый контракт для всех агентных ролей."""

    name: str
    description: str

    def invoke(self, input_data: BaseModel | dict[str, Any], context: AgentContext) -> AgentResult:
        """Запускает агент и возвращает стандартизованный результат."""

    def supports_tools(self) -> bool:
        """Показывает, умеет ли агент вызывать инструменты."""

    def supports_structured_output(self) -> bool:
        """Показывает, поддерживает ли агент строгое структурное представление ответа."""

    def build_prompt(self, input_data: BaseModel | dict[str, Any], context: AgentContext) -> str:
        """Собирает промпт для модельного gateway."""

    def handle_result(self, model_output: str, context: AgentContext) -> AgentResult:
        """Преобразует сырой ответ модели в контракт результата агента."""
