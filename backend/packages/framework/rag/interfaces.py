from __future__ import annotations

from typing import Protocol, runtime_checkable

from schemas.rag.contracts import EvidencePack, RerankedBlock, RetrievedBlock, RetrievalFilter


@runtime_checkable
class IRetriever(Protocol):
    """Контракт retriever-компонента."""

    def retrieve(self, query: str, filters: RetrievalFilter) -> list[RetrievedBlock]:
        """Возвращает кандидаты по запросу и фильтрам."""


@runtime_checkable
class IReranker(Protocol):
    """Контракт reranker-компонента."""

    def rerank(self, query: str, candidates: list[RetrievedBlock]) -> list[RerankedBlock]:
        """Переупорядочивает кандидаты по релевантности."""


@runtime_checkable
class IEvidenceBuilder(Protocol):
    """Контракт сборщика evidence pack."""

    def build(self, reranked_blocks: list[RerankedBlock]) -> EvidencePack:
        """Собирает нормализованный evidence pack."""
