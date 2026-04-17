from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel


@runtime_checkable
class IWorkflow(Protocol):
    """Контракт workflow, исполняемого через LangGraph runtime."""

    def state_schema(self) -> type[BaseModel]:
        """Возвращает тип состояния workflow."""

    def compile(self) -> Any:
        """Компилирует graph-структуру в runtime-объект."""

    def invoke(self, payload: BaseModel | dict[str, Any]) -> BaseModel:
        """Запускает workflow c начальным payload."""

    def resume(self, payload: BaseModel | dict[str, Any]) -> BaseModel:
        """Возобновляет workflow после interrupt."""
