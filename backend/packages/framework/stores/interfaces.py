from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class IDocumentStore(Protocol):
    """Контракт доступа к исходным документам и их версиям."""

    def read_document(self, doc_id: str) -> dict[str, Any]:
        """Читает документ по идентификатору."""


@runtime_checkable
class IKnowledgeStore(Protocol):
    """Контракт работы с каноническими документами и knowledge-блоками."""

    def upsert_knowledge_block(self, payload: dict[str, Any]) -> str:
        """Создает или обновляет knowledge-блок."""


@runtime_checkable
class IVectorStore(Protocol):
    """Контракт векторного хранилища."""

    def upsert_vector(self, key: str, vector: list[float], metadata: dict[str, Any]) -> None:
        """Сохраняет вектор и его метаданные."""


@runtime_checkable
class ICheckpointStore(Protocol):
    """Контракт хранения checkpoint-состояния."""

    def save_checkpoint(self, run_id: str, payload: dict[str, Any]) -> None:
        """Сохраняет checkpoint процесса."""

    def load_checkpoint(self, run_id: str) -> dict[str, Any] | None:
        """Загружает checkpoint процесса."""


@runtime_checkable
class IArtifactStore(Protocol):
    """Контракт хранения сгенерированных артефактов."""

    def save_artifact(self, artifact_id: str, payload: dict[str, Any]) -> None:
        """Сохраняет артефакт в целевом хранилище."""
