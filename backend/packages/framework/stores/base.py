from __future__ import annotations

from typing import Any

from framework.stores.interfaces import IArtifactStore, IDocumentStore, IKnowledgeStore, IVectorStore


class BaseDocumentStore(IDocumentStore):
    """Базовая in-memory заглушка document store."""

    def read_document(self, doc_id: str) -> dict[str, Any]:
        raise NotImplementedError("BaseDocumentStore.read_document не реализован")


class BaseKnowledgeStore(IKnowledgeStore):
    """Базовая in-memory заглушка knowledge store."""

    def upsert_knowledge_block(self, payload: dict[str, Any]) -> str:
        raise NotImplementedError("BaseKnowledgeStore.upsert_knowledge_block не реализован")


class BaseVectorStore(IVectorStore):
    """Базовая in-memory заглушка vector store."""

    def upsert_vector(self, key: str, vector: list[float], metadata: dict[str, Any]) -> None:
        raise NotImplementedError("BaseVectorStore.upsert_vector не реализован")


class BaseArtifactStore(IArtifactStore):
    """Базовая in-memory заглушка artifact store."""

    def save_artifact(self, artifact_id: str, payload: dict[str, Any]) -> None:
        raise NotImplementedError("BaseArtifactStore.save_artifact не реализован")