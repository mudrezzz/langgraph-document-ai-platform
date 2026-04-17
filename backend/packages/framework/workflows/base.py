from __future__ import annotations

from abc import ABC
from typing import Any

from pydantic import BaseModel

from framework.workflows.interfaces import IWorkflow


class BaseWorkflow(ABC, IWorkflow):
    """Тонкая абстракция над lifecycle workflow."""

    def __init__(self) -> None:
        self._compiled_graph: Any | None = None

    def compile(self) -> Any:
        # В текущем инкременте это placeholder до подключения реального LangGraph builder.
        self._compiled_graph = {"status": "compiled", "workflow": self.__class__.__name__}
        return self._compiled_graph

    def invoke(self, payload: BaseModel | dict[str, Any]) -> BaseModel:
        state = self.state_schema().model_validate(payload)
        return state

    def resume(self, payload: BaseModel | dict[str, Any]) -> BaseModel:
        state = self.state_schema().model_validate(payload)
        return state
