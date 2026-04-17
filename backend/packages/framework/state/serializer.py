from __future__ import annotations

from pydantic import BaseModel


class StateSerializer:
    """Сериализация и десериализация состояния workflow."""

    def dumps(self, state: BaseModel) -> dict:
        # Сериализуем в JSON-совместимый словарь для хранения в checkpoint store.
        return state.model_dump(mode="json")

    def loads(self, state_type: type[BaseModel], payload: dict) -> BaseModel:
        return state_type.model_validate(payload)
