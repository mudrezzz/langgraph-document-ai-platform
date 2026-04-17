from __future__ import annotations

from framework.stores.interfaces import ICheckpointStore


class LangGraphPostgresCheckpointStore(ICheckpointStore):
    """Скелет checkpoint store для LangGraph на базе PostgreSQL."""

    def __init__(self) -> None:
        self._checkpoints: dict[str, dict] = {}

    def save_checkpoint(self, run_id: str, payload: dict) -> None:
        self._checkpoints[run_id] = payload

    def load_checkpoint(self, run_id: str) -> dict | None:
        return self._checkpoints.get(run_id)