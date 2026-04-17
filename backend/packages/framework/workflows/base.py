from __future__ import annotations

from abc import ABC
from typing import Any

from pydantic import BaseModel

from framework.workflows.interfaces import IWorkflow

try:
    from langgraph.graph import END, START, StateGraph

    LANGGRAPH_AVAILABLE = True
except Exception:  # pragma: no cover - защитная ветка для окружений без langgraph
    LANGGRAPH_AVAILABLE = False
    START = "START"
    END = "END"
    StateGraph = None  # type: ignore[assignment]


class BaseWorkflow(ABC, IWorkflow):
    """Базовая абстракция workflow с поддержкой LangGraph runtime."""

    def __init__(self, use_langgraph_runtime: bool = True) -> None:
        self._use_langgraph_runtime = use_langgraph_runtime
        self._compiled_graph: Any | None = None
        self._compiled_resume_graph: Any | None = None
        self._runtime_mode: str = "fallback"

    def compile(self) -> Any:
        """Компилирует графы invoke/resume через LangGraph при доступности пакета."""

        if self._use_langgraph_runtime and LANGGRAPH_AVAILABLE:
            self._compiled_graph = self._compile_graph(entry_node_name="invoke_entry", is_resume=False)
            self._compiled_resume_graph = self._compile_graph(entry_node_name="resume_entry", is_resume=True)
            self._runtime_mode = "langgraph"
        else:
            # Fallback-режим: сохраняем диагностический объект вместо graph runtime.
            self._compiled_graph = {"status": "compiled", "workflow": self.__class__.__name__}
            self._compiled_resume_graph = self._compiled_graph
            self._runtime_mode = "fallback"

        return {
            "workflow": self.__class__.__name__,
            "runtime_mode": self._runtime_mode,
            "invoke_graph_ready": self._compiled_graph is not None,
            "resume_graph_ready": self._compiled_resume_graph is not None,
        }

    def invoke(self, payload: BaseModel | dict[str, Any]) -> BaseModel:
        """Запускает workflow с автоматическим выбором runtime-режима."""

        state = self.state_schema().model_validate(payload)
        if self._runtime_mode == "langgraph":
            return self._invoke_langgraph(state, is_resume=False)
        return self.execute(state)

    def resume(self, payload: BaseModel | dict[str, Any]) -> BaseModel:
        """Возобновляет workflow после checkpoint/interrupt."""

        state = self.state_schema().model_validate(payload)
        if self._runtime_mode == "langgraph":
            return self._invoke_langgraph(state, is_resume=True)
        return self.execute_resume(state)

    def execute(self, state: BaseModel) -> BaseModel:
        """Основная бизнес-логика workflow для invoke-пути."""

        return state

    def execute_resume(self, state: BaseModel) -> BaseModel:
        """Бизнес-логика resume-пути по умолчанию."""

        return state

    def _compile_graph(self, entry_node_name: str, is_resume: bool) -> Any:
        """Строит одношаговый LangGraph, делегирующий логику в execute/execute_resume."""

        if StateGraph is None:  # pragma: no cover
            raise RuntimeError("LangGraph недоступен")

        builder = StateGraph(dict)

        def _entry_node(state_payload: dict[str, Any]) -> dict[str, Any]:
            # В узле валидируем payload по state_schema и выполняем нужную ветку.
            state_obj = self.state_schema().model_validate(state_payload)
            result = self.execute_resume(state_obj) if is_resume else self.execute(state_obj)
            return result.model_dump(mode="json")

        builder.add_node(entry_node_name, _entry_node)
        builder.add_edge(START, entry_node_name)
        builder.add_edge(entry_node_name, END)

        return builder.compile()

    def _invoke_langgraph(self, state: BaseModel, is_resume: bool) -> BaseModel:
        """Выполняет compiled LangGraph и возвращает типизированный state."""

        if self._compiled_graph is None or self._compiled_resume_graph is None:
            self.compile()

        graph = self._compiled_resume_graph if is_resume else self._compiled_graph
        if graph is None:
            raise RuntimeError("Граф workflow не скомпилирован")

        result_payload = graph.invoke(state.model_dump(mode="json"))
        return self.state_schema().model_validate(result_payload)