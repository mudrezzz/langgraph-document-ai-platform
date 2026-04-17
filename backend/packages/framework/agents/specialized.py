from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from framework.agents.base import BaseAgent
from framework.agents.interfaces import AgentContext, AgentResult


class ToolAgent(BaseAgent):
    """Агент, поддерживающий работу с инструментами."""

    def supports_tools(self) -> bool:
        return True


class SupervisorAgent(BaseAgent):
    """Агент-маршрутизатор, возвращающий решение о следующем шаге."""

    def supports_structured_output(self) -> bool:
        return True

    def handle_result(self, model_output: str, context: AgentContext) -> AgentResult:
        # Пока возвращаем простую структуру; в следующих инкрементах добавим строгий routing artifact.
        return AgentResult(raw_output={"decision": model_output}, metadata={"role": "supervisor"})


class ReviewAgent(BaseAgent):
    """Агент локального ревью результата section-level генерации."""

    def supports_structured_output(self) -> bool:
        return True


class HumanGateAgent(BaseAgent):
    """Агент-граница для явного перехода в HITL interrupt."""

    def invoke(self, input_data: BaseModel | dict[str, Any], context: AgentContext) -> AgentResult:
        # На текущем этапе агент только помечает необходимость ручного решения.
        return AgentResult(raw_output={"status": "human_required", "input": input_data})