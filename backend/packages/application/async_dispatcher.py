from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Protocol


class AuthoringAsyncDispatcher(Protocol):
    """Контракт постановки authoring-задач в асинхронное исполнение."""

    def enqueue_authoring_start(self, *, task_id: str, request_payload: dict) -> str:
        """Ставит задачу запуска authoring flow в очередь и возвращает dispatch id."""

    def enqueue_hitl_action(self, *, task_id: str, action_payload: dict) -> str:
        """Ставит в очередь обработку ручного HITL-решения и возвращает dispatch id."""


class KnowledgeIndexingAsyncDispatcher(Protocol):
    """Контракт постановки knowledge indexing задач в асинхронное исполнение."""

    def enqueue_knowledge_indexing_start(self, *, task_id: str, request_payload: dict) -> str:
        """Ставит задачу запуска knowledge indexing flow в очередь и возвращает dispatch id."""


class RetrievalAsyncDispatcher(Protocol):
    """Контракт постановки retrieval-задач в асинхронное исполнение."""

    def enqueue_retrieval_start(self, *, task_id: str, request_payload: dict) -> str:
        """Ставит задачу запуска retrieval flow в очередь и возвращает dispatch id."""


@dataclass(slots=True)
class InlineAuthoringAsyncDispatcher:
    """Локальный dispatcher для dev/test: выполняет задачу синхронно."""

    runner: Callable[[str, dict], Any]
    hitl_runner: Callable[[str, dict], Any]

    def enqueue_authoring_start(self, *, task_id: str, request_payload: dict) -> str:
        # Для локального режима выполняем задачу сразу, сохраняя API контракт async endpoint.
        self.runner(task_id, request_payload)
        return f"inline-{task_id}"

    def enqueue_hitl_action(self, *, task_id: str, action_payload: dict) -> str:
        # В inline-режиме продолжение HITL выполняем синхронно.
        self.hitl_runner(task_id, action_payload)
        return f"inline-hitl-{task_id}"


@dataclass(slots=True)
class InlineKnowledgeIndexingAsyncDispatcher:
    """Локальный dispatcher для dev/test: выполняет indexing синхронно."""

    runner: Callable[[str, dict], Any]

    def enqueue_knowledge_indexing_start(self, *, task_id: str, request_payload: dict) -> str:
        self.runner(task_id, request_payload)
        return f"inline-knowledge-indexing-{task_id}"


@dataclass(slots=True)
class InlineRetrievalAsyncDispatcher:
    """Локальный dispatcher для dev/test: выполняет retrieval синхронно."""

    runner: Callable[[str, dict], Any]

    def enqueue_retrieval_start(self, *, task_id: str, request_payload: dict) -> str:
        self.runner(task_id, request_payload)
        return f"inline-retrieval-{task_id}"
