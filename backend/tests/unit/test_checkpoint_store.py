from infra.postgres.checkpoint_store import LangGraphPostgresCheckpointStore
from langgraph.graph import StateGraph


def test_checkpoint_store_roundtrip() -> None:
    store = LangGraphPostgresCheckpointStore()
    payload = {"node": "retrieval", "status": "running"}

    store.save_checkpoint("run-1", payload)
    restored = store.load_checkpoint("run-1")

    assert restored == payload


def test_checkpoint_store_builds_fallback_langgraph_checkpointer() -> None:
    store = LangGraphPostgresCheckpointStore(dsn=None, use_fallback_if_unset=True)

    checkpointer = store.build_langgraph_checkpointer()

    assert checkpointer is not None


def test_fallback_langgraph_checkpointer_persists_graph_state() -> None:
    store = LangGraphPostgresCheckpointStore(dsn=None, use_fallback_if_unset=True)
    checkpointer = store.build_langgraph_checkpointer()
    assert checkpointer is not None

    builder = StateGraph(dict)
    builder.add_node("increment", lambda state: {"value": state["value"] + 1})
    builder.set_entry_point("increment")
    builder.set_finish_point("increment")
    graph = builder.compile(checkpointer=checkpointer)

    result = graph.invoke({"value": 1}, config={"configurable": {"thread_id": "thread-1"}})
    assert result["value"] == 2

    checkpoint = checkpointer.get_tuple({"configurable": {"thread_id": "thread-1"}})
    assert checkpoint is not None
    assert checkpoint.config["configurable"]["thread_id"] == "thread-1"
