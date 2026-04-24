from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from framework.workflows.interfaces import IWorkflow

WorkflowBuilder = Callable[..., IWorkflow]


class WorkflowFactoryError(Exception):
    """Base error for workflow factory operations."""


class WorkflowRegistrationError(WorkflowFactoryError, ValueError):
    """Raised when workflow registration is invalid."""


class WorkflowNotRegisteredError(WorkflowFactoryError, KeyError):
    """Raised when requested workflow key is absent."""


@dataclass(frozen=True)
class WorkflowRegistration:
    """Registered workflow builder and optional capability metadata."""

    key: str
    builder: WorkflowBuilder
    metadata: dict[str, Any] = field(default_factory=dict)


class WorkflowFactory:
    """Фабрика workflow-объектов по строковому ключу."""

    def __init__(self) -> None:
        self._registry: dict[str, WorkflowRegistration] = {}

    def register(
        self,
        key: str,
        workflow_type: type[IWorkflow] | WorkflowBuilder,
        *,
        metadata: dict[str, Any] | None = None,
        replace: bool = False,
    ) -> None:
        self.register_builder(key, workflow_type, metadata=metadata, replace=replace)

    def register_builder(
        self,
        key: str,
        builder: WorkflowBuilder,
        *,
        metadata: dict[str, Any] | None = None,
        replace: bool = False,
    ) -> None:
        normalized_key = self._normalize_key(key)
        if not callable(builder):
            raise WorkflowRegistrationError(
                f"Workflow builder for key `{normalized_key}` must be callable."
            )
        if normalized_key in self._registry and not replace:
            raise WorkflowRegistrationError(f"Workflow `{normalized_key}` is already registered.")
        self._registry[normalized_key] = WorkflowRegistration(
            key=normalized_key,
            builder=builder,
            metadata=dict(metadata or {}),
        )

    def build(self, key: str, **dependencies: Any) -> IWorkflow:
        registration = self._registry.get(self._normalize_key(key))
        if registration is None:
            raise WorkflowNotRegisteredError(f"Workflow `{key}` is not registered.")
        return registration.builder(**dependencies)

    def has(self, key: str) -> bool:
        return self._normalize_key(key) in self._registry

    def list_workflows(self) -> list[str]:
        return sorted(self._registry)

    def metadata(self, key: str) -> dict[str, Any]:
        registration = self._registry.get(self._normalize_key(key))
        if registration is None:
            raise WorkflowNotRegisteredError(f"Workflow `{key}` is not registered.")
        return dict(registration.metadata)

    def _normalize_key(self, key: str) -> str:
        normalized_key = key.strip()
        if not normalized_key:
            raise WorkflowRegistrationError("Workflow key must be a non-empty string.")
        return normalized_key
