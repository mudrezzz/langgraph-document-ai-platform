from __future__ import annotations

from abc import ABC
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import Any, Protocol

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


@dataclass(frozen=True, slots=True)
class WorkflowExecutionContext:
    """Typed runtime context для workflow node execution."""

    workflow_name: str
    node_name: str
    task_id: str | None = None
    correlation_id: str | None = None
    is_resume: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def for_node(self, node_name: str) -> "WorkflowExecutionContext":
        return WorkflowExecutionContext(
            workflow_name=self.workflow_name,
            node_name=node_name,
            task_id=self.task_id,
            correlation_id=self.correlation_id,
            is_resume=self.is_resume,
            metadata=dict(self.metadata),
        )


@dataclass(frozen=True, slots=True)
class WorkflowNodeSpec:
    """Описание одного sequential node внутри framework workflow."""

    name: str
    handler: Callable[[BaseModel, WorkflowExecutionContext], BaseModel]
    next_node: str | None = None

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("WorkflowNodeSpec.name не должен быть пустым")


@dataclass(frozen=True, slots=True)
class WorkflowNodeEventRecord:
    """Audit event emitted by BaseWorkflow around one node execution."""

    workflow_name: str
    node_name: str
    status: str
    task_id: str | None = None
    correlation_id: str | None = None
    is_resume: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)
    error: str | None = None


class WorkflowNodeEventSink(Protocol):
    """Port for recording workflow node-level audit events."""

    def record_node_event(self, event: WorkflowNodeEventRecord) -> None:
        """Persist or forward a workflow node event."""


class BaseWorkflow(ABC, IWorkflow):
    """Базовая абстракция workflow с поддержкой LangGraph runtime."""

    def __init__(
        self,
        use_langgraph_runtime: bool = True,
        checkpointer: Any | None = None,
        node_event_sink: WorkflowNodeEventSink | None = None,
    ) -> None:
        self._use_langgraph_runtime = use_langgraph_runtime
        self._langgraph_checkpointer = checkpointer
        self._node_event_sink = node_event_sink
        self._compiled_graph: Any | None = None
        self._compiled_resume_graph: Any | None = None
        self._runtime_mode: str = "fallback"

    def compile(self) -> Any:
        """Компилирует графы invoke/resume через LangGraph при доступности пакета."""

        if self._use_langgraph_runtime and LANGGRAPH_AVAILABLE:
            invoke_nodes = self.workflow_nodes(is_resume=False)
            resume_nodes = self.workflow_nodes(is_resume=True)
            self._compiled_graph = self._compile_graph(invoke_nodes, is_resume=False)
            self._compiled_resume_graph = self._compile_graph(resume_nodes, is_resume=True)
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
            "invoke_node_count": len(self.workflow_nodes(is_resume=False)),
            "resume_node_count": len(self.workflow_nodes(is_resume=True)),
        }

    def invoke(self, payload: BaseModel | dict[str, Any]) -> BaseModel:
        """Запускает workflow с автоматическим выбором runtime-режима."""

        state = self.state_schema().model_validate(payload)
        if self._runtime_mode == "langgraph":
            return self._invoke_langgraph(state, is_resume=False)
        return self._run_fallback_nodes(state, is_resume=False)

    def resume(self, payload: BaseModel | dict[str, Any]) -> BaseModel:
        """Возобновляет workflow после checkpoint/interrupt."""

        state = self.state_schema().model_validate(payload)
        if self._runtime_mode == "langgraph":
            return self._invoke_langgraph(state, is_resume=True)
        return self._run_fallback_nodes(state, is_resume=True)

    def execute(self, state: BaseModel) -> BaseModel:
        """Основная бизнес-логика workflow для invoke-пути."""

        return state

    def execute_resume(self, state: BaseModel) -> BaseModel:
        """Бизнес-логика resume-пути по умолчанию."""

        return state

    def workflow_nodes(self, *, is_resume: bool) -> Sequence[WorkflowNodeSpec]:
        """Возвращает sequential node specs для invoke/resume graph.

        Subclasses can override this hook to build multi-node workflows while
        keeping common compile/invoke/checkpointer behavior in BaseWorkflow.
        """

        node_name = "resume_entry" if is_resume else "invoke_entry"
        handler = self._execute_resume_node if is_resume else self._execute_node
        return [WorkflowNodeSpec(name=node_name, handler=handler)]

    def _execute_node(self, state: BaseModel, context: WorkflowExecutionContext) -> BaseModel:
        _ = context
        return self.execute(state)

    def _execute_resume_node(self, state: BaseModel, context: WorkflowExecutionContext) -> BaseModel:
        _ = context
        return self.execute_resume(state)

    def _compile_graph(self, node_specs: Sequence[WorkflowNodeSpec], *, is_resume: bool) -> Any:
        """Строит LangGraph из sequential node specs."""

        if StateGraph is None:  # pragma: no cover
            raise RuntimeError("LangGraph недоступен")
        if not node_specs:
            raise ValueError("Workflow должен содержать хотя бы один node")

        builder = StateGraph(dict)
        node_names = [node.name for node in node_specs]
        if len(node_names) != len(set(node_names)):
            raise ValueError(f"Workflow содержит повторяющиеся node names: {node_names}")

        for node_spec in node_specs:
            builder.add_node(node_spec.name, self._build_langgraph_node(node_spec, is_resume=is_resume))

        builder.add_edge(START, node_specs[0].name)
        for index, node_spec in enumerate(node_specs):
            next_node = node_spec.next_node
            if next_node is None and index + 1 < len(node_specs):
                next_node = node_specs[index + 1].name
            builder.add_edge(node_spec.name, next_node or END)

        return builder.compile(checkpointer=self._langgraph_checkpointer)

    def _build_langgraph_node(self, node_spec: WorkflowNodeSpec, *, is_resume: bool) -> Callable[[dict[str, Any]], dict[str, Any]]:
        def _node(state_payload: dict[str, Any]) -> dict[str, Any]:
            state_obj = self.state_schema().model_validate(state_payload)
            context = self._build_execution_context(state_obj, node_name=node_spec.name, is_resume=is_resume)
            result = self._execute_node_spec(node_spec, state_obj, context)
            return result.model_dump(mode="json")

        return _node

    def _invoke_langgraph(self, state: BaseModel, is_resume: bool) -> BaseModel:
        """Выполняет compiled LangGraph и возвращает типизированный state."""

        if self._compiled_graph is None or self._compiled_resume_graph is None:
            self.compile()

        graph = self._compiled_resume_graph if is_resume else self._compiled_graph
        if graph is None:
            raise RuntimeError("Граф workflow не скомпилирован")

        invoke_config = self._build_langgraph_config(state)
        state_payload = state.model_dump(mode="json")
        if invoke_config is None:
            result_payload = graph.invoke(state_payload)
        else:
            result_payload = graph.invoke(state_payload, config=invoke_config)
        return self.state_schema().model_validate(result_payload)

    def _run_fallback_nodes(self, state: BaseModel, *, is_resume: bool) -> BaseModel:
        node_specs = self.workflow_nodes(is_resume=is_resume)
        if not node_specs:
            raise ValueError("Workflow должен содержать хотя бы один node")
        current_state = state
        for node_spec in node_specs:
            context = self._build_execution_context(current_state, node_name=node_spec.name, is_resume=is_resume)
            current_state = self._execute_node_spec(node_spec, current_state, context)
        return self.state_schema().model_validate(current_state)

    def _execute_node_spec(
        self,
        node_spec: WorkflowNodeSpec,
        state: BaseModel,
        context: WorkflowExecutionContext,
    ) -> BaseModel:
        self._record_node_event(context, status="started")
        try:
            result = self.state_schema().model_validate(node_spec.handler(state, context))
        except Exception as exc:
            self._record_node_event(context, status="failed", error=str(exc))
            raise

        self._record_node_event(context, status="completed")
        return result

    def _record_node_event(
        self,
        context: WorkflowExecutionContext,
        *,
        status: str,
        error: str | None = None,
    ) -> None:
        if self._node_event_sink is None:
            return
        self._node_event_sink.record_node_event(
            WorkflowNodeEventRecord(
                workflow_name=context.workflow_name,
                node_name=context.node_name,
                task_id=context.task_id,
                correlation_id=context.correlation_id,
                is_resume=context.is_resume,
                metadata=dict(context.metadata),
                status=status,
                error=error,
            )
        )

    def _build_execution_context(
        self,
        state: BaseModel,
        *,
        node_name: str,
        is_resume: bool,
    ) -> WorkflowExecutionContext:
        task_context = getattr(state, "task_context", None)
        metadata = dict(task_context) if isinstance(task_context, dict) else {}
        task_id = self._optional_task_id(state)
        correlation_id = None
        if isinstance(task_context, dict):
            candidate = task_context.get("correlation_id")
            if isinstance(candidate, str) and candidate.strip():
                correlation_id = candidate

        return WorkflowExecutionContext(
            workflow_name=self.__class__.__name__,
            node_name=node_name,
            task_id=task_id,
            correlation_id=correlation_id,
            is_resume=is_resume,
            metadata=metadata,
        )

    def _build_langgraph_config(self, state: BaseModel) -> dict[str, Any] | None:
        """Строит runtime-config для LangGraph; при checkpointer обязателен `thread_id`."""

        if self._langgraph_checkpointer is None:
            return None

        thread_id = self._resolve_thread_id(state)
        return {"configurable": {"thread_id": thread_id}}

    @staticmethod
    def _resolve_thread_id(state: BaseModel) -> str:
        """Извлекает thread_id из state для устойчивого checkpointing."""

        task_context = getattr(state, "task_context", None)
        if isinstance(task_context, dict):
            candidate = task_context.get("task_id")
            if isinstance(candidate, str) and candidate.strip():
                return candidate

        candidate = getattr(state, "task_id", None)
        if isinstance(candidate, str) and candidate.strip():
            return candidate

        raise ValueError("Для LangGraph checkpointer требуется task_id в state.task_context или state.task_id")

    @staticmethod
    def _optional_task_id(state: BaseModel) -> str | None:
        task_context = getattr(state, "task_context", None)
        if isinstance(task_context, dict):
            candidate = task_context.get("task_id")
            if isinstance(candidate, str) and candidate.strip():
                return candidate

        candidate = getattr(state, "task_id", None)
        if isinstance(candidate, str) and candidate.strip():
            return candidate

        return None
