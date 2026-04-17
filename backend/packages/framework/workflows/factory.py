from __future__ import annotations

from framework.workflows.interfaces import IWorkflow


class WorkflowFactory:
    """Фабрика workflow-объектов по строковому ключу."""

    def __init__(self) -> None:
        self._registry: dict[str, type[IWorkflow]] = {}

    def register(self, key: str, workflow_type: type[IWorkflow]) -> None:
        self._registry[key] = workflow_type

    def build(self, key: str) -> IWorkflow:
        workflow_type = self._registry[key]
        return workflow_type()