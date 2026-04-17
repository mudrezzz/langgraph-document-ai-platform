from __future__ import annotations

from pydantic import BaseModel

from framework.workflows.base import BaseWorkflow


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


def test_base_workflow_uses_langgraph_runtime_for_invoke_and_resume() -> None:
    workflow = DummyWorkflow()

    meta = workflow.compile()
    assert meta["runtime_mode"] == "langgraph"

    invoked = workflow.invoke({"value": 1})
    resumed = workflow.resume({"value": 1})

    assert invoked.value == 2
    assert resumed.value == 11