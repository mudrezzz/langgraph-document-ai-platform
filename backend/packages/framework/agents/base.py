from __future__ import annotations

from abc import ABC
from typing import Any

from pydantic import BaseModel

from framework.agents.interfaces import AgentContext, AgentResult, IAgent
from framework.models.interfaces import IChatModelGateway


class BaseAgent(ABC, IAgent):
    """Базовая реализация жизненного цикла агента."""

    def __init__(self, name: str, description: str, model_gateway: IChatModelGateway) -> None:
        self.name = name
        self.description = description
        self._model_gateway = model_gateway

    def invoke(self, input_data: BaseModel | dict[str, Any], context: AgentContext) -> AgentResult:
        # Базовый pipeline: промпт -> вызов модели -> нормализация результата.
        prompt = self.build_prompt(input_data, context)
        raw_output = self._model_gateway.generate(prompt, metadata=context.metadata)
        return self.handle_result(raw_output, context)

    def supports_tools(self) -> bool:
        return False

    def supports_structured_output(self) -> bool:
        return False

    def build_prompt(self, input_data: BaseModel | dict[str, Any], context: AgentContext) -> str:
        return f"[{self.name}] node={context.node_name}; input={input_data}"

    def handle_result(self, model_output: str, context: AgentContext) -> AgentResult:
        return AgentResult(raw_output=model_output, metadata={"agent": self.name})
