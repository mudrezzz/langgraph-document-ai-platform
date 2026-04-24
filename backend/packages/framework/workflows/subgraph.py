from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from framework.workflows.base import BaseWorkflow, WorkflowExecutionContext, WorkflowNodeEventSink


class SubgraphWorkflow(BaseWorkflow):
    """Повторно используемый subgraph-процесс с parent context propagation."""

    def __init__(
        self,
        *,
        subgraph_name: str | None = None,
        use_langgraph_runtime: bool = True,
        checkpointer: Any | None = None,
        node_event_sink: WorkflowNodeEventSink | None = None,
    ) -> None:
        super().__init__(
            use_langgraph_runtime=use_langgraph_runtime,
            checkpointer=checkpointer,
            node_event_sink=node_event_sink,
        )
        self._subgraph_name = subgraph_name or self.__class__.__name__

    @property
    def subgraph_name(self) -> str:
        return self._subgraph_name

    def invoke_as_subgraph(
        self,
        payload: BaseModel | dict[str, Any],
        *,
        parent_context: WorkflowExecutionContext | None = None,
    ) -> BaseModel:
        state = self.state_schema().model_validate(payload)
        if parent_context is None:
            return self.invoke(state)

        state = self._merge_parent_context(state, parent_context=parent_context)
        return self.invoke(state)

    def _build_execution_context(
        self,
        state: BaseModel,
        *,
        node_name: str,
        is_resume: bool,
    ) -> WorkflowExecutionContext:
        context = super()._build_execution_context(state, node_name=node_name, is_resume=is_resume)
        metadata = dict(context.metadata)
        metadata.setdefault("subgraph_name", self._subgraph_name)
        return WorkflowExecutionContext(
            workflow_name=context.workflow_name,
            node_name=context.node_name,
            task_id=context.task_id,
            correlation_id=context.correlation_id,
            is_resume=context.is_resume,
            metadata=metadata,
        )

    def _merge_parent_context(
        self,
        state: BaseModel,
        *,
        parent_context: WorkflowExecutionContext,
    ) -> BaseModel:
        task_context = getattr(state, "task_context", None)
        if not isinstance(task_context, dict):
            return state

        merged = dict(task_context)
        if parent_context.task_id:
            merged.setdefault("task_id", parent_context.task_id)
        if parent_context.correlation_id:
            merged.setdefault("correlation_id", parent_context.correlation_id)
        merged.setdefault("parent_workflow_name", parent_context.workflow_name)
        merged.setdefault("parent_node_name", parent_context.node_name)
        merged.setdefault("subgraph_name", self._subgraph_name)
        return state.model_copy(update={"task_context": merged})
