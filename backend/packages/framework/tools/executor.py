from __future__ import annotations

from dataclasses import dataclass, field
from time import monotonic
from typing import Any, Protocol

from pydantic import BaseModel

from framework.tools.interfaces import ToolContext
from framework.tools.registry import ToolRegistry


@dataclass(frozen=True, slots=True)
class ToolExecutionPolicy:
    """Runtime policy для выполнения framework tools."""

    max_attempts: int = 1
    timeout_sec: float | None = None
    idempotency_enabled: bool = True
    audit_enabled: bool = True

    def __post_init__(self) -> None:
        if self.max_attempts < 1:
            raise ValueError("ToolExecutionPolicy.max_attempts должен быть >= 1")
        if self.timeout_sec is not None and self.timeout_sec <= 0:
            raise ValueError("ToolExecutionPolicy.timeout_sec должен быть > 0")


@dataclass(frozen=True, slots=True)
class ToolExecutionRecord:
    """Audit-запись выполнения tool call."""

    tool_name: str
    task_id: str
    actor: str
    attempt: int
    status: str
    elapsed_sec: float
    node_name: str | None = None
    correlation_id: str | None = None
    idempotency_key: str | None = None
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class ToolExecutionAuditSink(Protocol):
    """Минимальный порт записи audit-событий tool execution."""

    def record(self, record: ToolExecutionRecord) -> None:
        """Сохраняет audit-запись."""


class InMemoryToolExecutionAuditSink:
    """In-memory audit sink для unit/dev сценариев."""

    def __init__(self) -> None:
        self.records: list[ToolExecutionRecord] = []

    def record(self, record: ToolExecutionRecord) -> None:
        self.records.append(record)


class ToolExecutor:
    """Унифицированный исполнитель инструментов с runtime policy."""

    def __init__(
        self,
        registry: ToolRegistry,
        *,
        policy: ToolExecutionPolicy | None = None,
        audit_sink: ToolExecutionAuditSink | None = None,
    ) -> None:
        self._registry = registry
        self._policy = policy or ToolExecutionPolicy()
        self._audit_sink = audit_sink
        self._idempotency_cache: dict[tuple[str, str], BaseModel] = {}

    def execute(self, tool_name: str, command: BaseModel, context: ToolContext) -> BaseModel:
        """Выполняет tool с retry/idempotency/audit policy."""

        cache_key = self._cache_key(tool_name, context)
        if cache_key is not None and cache_key in self._idempotency_cache:
            cached = self._idempotency_cache[cache_key]
            self._record(
                tool_name=tool_name,
                context=context,
                attempt=0,
                status="cached",
                elapsed_sec=0.0,
            )
            return cached

        tool = self._registry.get(tool_name)
        last_error: Exception | None = None

        for attempt in range(1, self._policy.max_attempts + 1):
            started_at = monotonic()
            try:
                result = tool.execute(command, context)
                elapsed_sec = monotonic() - started_at
                if self._policy.timeout_sec is not None and elapsed_sec > self._policy.timeout_sec:
                    raise TimeoutError(f"Tool `{tool_name}` exceeded timeout_sec={self._policy.timeout_sec}")
                if cache_key is not None:
                    self._idempotency_cache[cache_key] = result
                self._record(
                    tool_name=tool_name,
                    context=context,
                    attempt=attempt,
                    status="succeeded",
                    elapsed_sec=elapsed_sec,
                )
                return result
            except Exception as exc:
                elapsed_sec = monotonic() - started_at
                last_error = exc
                self._record(
                    tool_name=tool_name,
                    context=context,
                    attempt=attempt,
                    status="failed",
                    elapsed_sec=elapsed_sec,
                    error=str(exc),
                )

        if last_error is not None:
            raise last_error
        raise RuntimeError(f"Tool `{tool_name}` не был выполнен")

    def _cache_key(self, tool_name: str, context: ToolContext) -> tuple[str, str] | None:
        if not self._policy.idempotency_enabled:
            return None
        if not context.idempotency_key:
            return None
        return (tool_name, context.idempotency_key)

    def _record(
        self,
        *,
        tool_name: str,
        context: ToolContext,
        attempt: int,
        status: str,
        elapsed_sec: float,
        error: str | None = None,
    ) -> None:
        if not self._policy.audit_enabled or self._audit_sink is None:
            return
        self._audit_sink.record(
            ToolExecutionRecord(
                tool_name=tool_name,
                task_id=context.task_id,
                actor=context.actor,
                node_name=context.node_name,
                correlation_id=context.correlation_id,
                idempotency_key=context.idempotency_key,
                attempt=attempt,
                status=status,
                elapsed_sec=elapsed_sec,
                error=error,
                metadata=dict(context.metadata),
            )
        )
