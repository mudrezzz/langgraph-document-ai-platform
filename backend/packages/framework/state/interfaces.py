from __future__ import annotations

from typing import Protocol, runtime_checkable

from pydantic import BaseModel


@runtime_checkable
class IStateModel(Protocol):
    """Контракт состояния workflow."""

    def to_payload(self) -> dict:
        """Преобразует объект состояния в сериализуемый payload."""


class BaseStateModel(BaseModel):
    """Базовая обертка над Pydantic-моделью состояния."""

    def to_payload(self) -> dict:
        return self.model_dump(mode="json")


class StatePatch(BaseModel):
    """Контракт частичного обновления состояния."""

    updates: dict
