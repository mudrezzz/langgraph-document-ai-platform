from __future__ import annotations

from pydantic import BaseModel, Field

from framework.workflows.base import BaseWorkflow
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
