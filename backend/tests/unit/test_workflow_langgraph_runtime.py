from __future__ import annotations

from pydantic import BaseModel, Field

from framework.workflows.base import BaseWorkflow, WorkflowExecutionContext, WorkflowNodeEventRecord, WorkflowNodeSpec
from framework.workflows.subgraph import SubgraphWorkflow
from langgraph.checkpoint.memory import InMemorySaver


class DummyState(BaseModel):
    value: int


class DummyWorkflow(BaseWorkflow):
    def __init__(self) -> None:
        super().__init__(use_langgraph_runtime=True)
        self.compile()

    def state_schema(self) -> type[DummyState]:
        return DummyState

    def execute(self, state: DummyState) -> DummyState:
        return state.model_copy(update={"value": state.value + 1})

    def execute_resume(self, state: DummyState) -> DummyState:
        return state.model_copy(update={"value": state.value + 10})


class CheckpointedState(BaseModel):
    value: int
    task_context: dict = Field(default_factory=dict)


class CheckpointedWorkflow(BaseWorkflow):
    def __init__(self) -> None:
        super().__init__(use_langgraph_runtime=True, checkpointer=InMemorySaver())
        self.compile()

    def state_schema(self) -> type[CheckpointedState]:
        return CheckpointedState

    def execute(self, state: CheckpointedState) -> CheckpointedState:
        return state.model_copy(update={"value": state.value + 1})

    def execute_resume(self, state: CheckpointedState) -> CheckpointedState:
        return state.model_copy(update={"value": state.value + 10})


class MultiNodeState(BaseModel):
    value: int
    history: list[str] = Field(default_factory=list)
    task_context: dict = Field(default_factory=dict)


class MultiNodeWorkflow(BaseWorkflow):
    def __init__(self, *, use_langgraph_runtime: bool = True, node_event_sink=None) -> None:
        super().__init__(use_langgraph_runtime=use_langgraph_runtime, node_event_sink=node_event_sink)
        self.compile()

    def state_schema(self) -> type[MultiNodeState]:
        return MultiNodeState

    def workflow_nodes(self, *, is_resume: bool):
        if is_resume:
            return [
                WorkflowNodeSpec(name="resume_prepare", handler=self._resume_prepare),
                WorkflowNodeSpec(name="resume_finalize", handler=self._resume_finalize),
            ]
        return [
            WorkflowNodeSpec(name="prepare", handler=self._prepare),
            WorkflowNodeSpec(name="finalize", handler=self._finalize),
        ]

    def _prepare(self, state: BaseModel, context: WorkflowExecutionContext) -> BaseModel:
        validated = MultiNodeState.model_validate(state)
        return validated.model_copy(
            update={
                "value": validated.value + 1,
                "history": [
                    *validated.history,
                    f"{context.node_name}:{context.task_id}:{context.correlation_id}",
                ],
            }
        )

    def _finalize(self, state: BaseModel, context: WorkflowExecutionContext) -> BaseModel:
        validated = MultiNodeState.model_validate(state)
        return validated.model_copy(
            update={
                "value": validated.value * 2,
                "history": [*validated.history, context.node_name],
            }
        )

    def _resume_prepare(self, state: BaseModel, context: WorkflowExecutionContext) -> BaseModel:
        validated = MultiNodeState.model_validate(state)
        return validated.model_copy(update={"history": [*validated.history, context.node_name]})

    def _resume_finalize(self, state: BaseModel, context: WorkflowExecutionContext) -> BaseModel:
        validated = MultiNodeState.model_validate(state)
        return validated.model_copy(
            update={
                "value": validated.value + 10,
                "history": [*validated.history, f"{context.node_name}:{context.is_resume}"],
            }
        )


class EchoSubgraph(SubgraphWorkflow):
    def __init__(self) -> None:
        super().__init__(subgraph_name="echo-subgraph", use_langgraph_runtime=True)
        self.contexts: list[WorkflowExecutionContext] = []
        self.compile()

    def state_schema(self) -> type[MultiNodeState]:
        return MultiNodeState

    def workflow_nodes(self, *, is_resume: bool):
        _ = is_resume
        return [WorkflowNodeSpec(name="echo", handler=self._echo)]

    def _echo(self, state: BaseModel, context: WorkflowExecutionContext) -> BaseModel:
        self.contexts.append(context)
        validated = MultiNodeState.model_validate(state)
        return validated.model_copy(update={"history": [*validated.history, context.metadata["parent_node_name"]]})


class FailingNodeWorkflow(BaseWorkflow):
    def __init__(self, *, node_event_sink=None) -> None:
        super().__init__(use_langgraph_runtime=True, node_event_sink=node_event_sink)
        self.compile()

    def state_schema(self) -> type[DummyState]:
        return DummyState

    def execute(self, state: DummyState) -> DummyState:
        _ = state
        raise RuntimeError("node failed")


class RecordingNodeEventSink:
    def __init__(self) -> None:
        self.events: list[WorkflowNodeEventRecord] = []

    def record_node_event(self, event: WorkflowNodeEventRecord) -> None:
        self.events.append(event)


def test_base_workflow_uses_langgraph_runtime_for_invoke_and_resume() -> None:
    workflow = DummyWorkflow()

    meta = workflow.compile()
    assert meta["runtime_mode"] == "langgraph"

    invoked = workflow.invoke({"value": 1})
    resumed = workflow.resume({"value": 1})

    assert invoked.value == 2
    assert resumed.value == 11


def test_base_workflow_uses_langgraph_checkpointer_with_task_id() -> None:
    workflow = CheckpointedWorkflow()

    invoked = workflow.invoke({"value": 5, "task_context": {"task_id": "task-1"}})
    resumed = workflow.resume({"value": 5, "task_context": {"task_id": "task-1"}})

    assert invoked.value == 6
    assert resumed.value == 15


def test_base_workflow_requires_task_id_when_checkpointer_is_enabled() -> None:
    workflow = CheckpointedWorkflow()

    try:
        workflow.invoke({"value": 5, "task_context": {}})
    except ValueError as exc:
        assert "task_id" in str(exc)
    else:
        raise AssertionError("Ожидалась ошибка отсутствия task_id для checkpointer")


def test_base_workflow_supports_multi_node_langgraph_execution_context() -> None:
    workflow = MultiNodeWorkflow()

    meta = workflow.compile()
    result = workflow.invoke(
        {
            "value": 2,
            "task_context": {
                "task_id": "task-2",
                "correlation_id": "corr-2",
            },
        }
    )

    assert meta["invoke_node_count"] == 2
    assert result.value == 6
    assert result.history == ["prepare:task-2:corr-2", "finalize"]


def test_base_workflow_supports_multi_node_resume_and_fallback_runtime() -> None:
    workflow = MultiNodeWorkflow(use_langgraph_runtime=False)

    invoked = workflow.invoke({"value": 3, "task_context": {"task_id": "task-3"}})
    resumed = workflow.resume({"value": 3, "task_context": {"task_id": "task-3"}})

    assert invoked.value == 8
    assert invoked.history == ["prepare:task-3:None", "finalize"]
    assert resumed.value == 13
    assert resumed.history == ["resume_prepare", "resume_finalize:True"]


def test_subgraph_workflow_propagates_parent_execution_context() -> None:
    subgraph = EchoSubgraph()
    parent_context = WorkflowExecutionContext(
        workflow_name="ParentWorkflow",
        node_name="parent_node",
        task_id="task-parent",
        correlation_id="corr-parent",
    )

    result = subgraph.invoke_as_subgraph({"value": 1, "task_context": {}}, parent_context=parent_context)

    assert result.task_context["task_id"] == "task-parent"
    assert result.task_context["correlation_id"] == "corr-parent"
    assert result.task_context["parent_workflow_name"] == "ParentWorkflow"
    assert result.task_context["subgraph_name"] == "echo-subgraph"
    assert result.history == ["parent_node"]
    assert subgraph.contexts[0].metadata["subgraph_name"] == "echo-subgraph"


def test_base_workflow_emits_node_events_for_success_and_failure() -> None:
    sink = RecordingNodeEventSink()
    workflow = MultiNodeWorkflow(node_event_sink=sink)

    result = workflow.invoke({"value": 1, "task_context": {"task_id": "task-node", "correlation_id": "corr-node"}})

    assert result.value == 4
    assert [(event.node_name, event.status) for event in sink.events] == [
        ("prepare", "started"),
        ("prepare", "completed"),
        ("finalize", "started"),
        ("finalize", "completed"),
    ]
    assert {event.task_id for event in sink.events} == {"task-node"}
    assert {event.correlation_id for event in sink.events} == {"corr-node"}

    failing_sink = RecordingNodeEventSink()
    failing_workflow = FailingNodeWorkflow(node_event_sink=failing_sink)

    try:
        failing_workflow.invoke({"value": 1})
    except RuntimeError:
        pass

    assert [(event.node_name, event.status) for event in failing_sink.events] == [
        ("invoke_entry", "started"),
        ("invoke_entry", "failed"),
    ]
    assert failing_sink.events[-1].error == "node failed"
