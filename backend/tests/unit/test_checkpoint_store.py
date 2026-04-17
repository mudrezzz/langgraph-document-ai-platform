from infra.postgres.checkpoint_store import LangGraphPostgresCheckpointStore


def test_checkpoint_store_roundtrip() -> None:
    store = LangGraphPostgresCheckpointStore()
    payload = {"node": "retrieval", "status": "running"}

    store.save_checkpoint("run-1", payload)
    restored = store.load_checkpoint("run-1")

    assert restored == payload