from framework.state.serializer import StateSerializer
from schemas.workflow.states import RetrievalWorkflowState


def test_state_serializer_roundtrip() -> None:
    serializer = StateSerializer()
    state = RetrievalWorkflowState(query="test")

    payload = serializer.dumps(state)
    restored = serializer.loads(RetrievalWorkflowState, payload)

    assert isinstance(restored, RetrievalWorkflowState)
    assert restored.query == "test"
