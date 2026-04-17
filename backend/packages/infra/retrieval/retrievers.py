from __future__ import annotations

from framework.rag.interfaces import IRetriever
from schemas.rag.contracts import RetrievedBlock, RetrievalFilter


class InMemoryRetriever(IRetriever):
    """In-memory retriever для summary/detail слоев в тестовом контуре."""

    def __init__(self, blocks: list[RetrievedBlock]) -> None:
        self._blocks = blocks

    def retrieve(self, query: str, filters: RetrievalFilter) -> list[RetrievedBlock]:
        # Упрощенный фильтр по типу документа и тегам.
        filtered = [block for block in self._blocks if self._matches_filter(block, filters)]
        # Простейший lexical score по вхождению токенов запроса.
        query_tokens = set(query.lower().split())
        scored: list[RetrievedBlock] = []
        for block in filtered:
            tokens = set(block.text.lower().split())
            overlap = len(tokens.intersection(query_tokens))
            scored.append(block.model_copy(update={"score": float(overlap)}))
        return sorted(scored, key=lambda block: block.score, reverse=True)

    def _matches_filter(self, block: RetrievedBlock, filters: RetrievalFilter) -> bool:
        metadata = block.metadata or {}

        if filters.document_types:
            doc_type = metadata.get("document_type")
            if doc_type not in filters.document_types:
                return False

        if filters.tags:
            tags = metadata.get("tags", [])
            if not any(tag in tags for tag in filters.tags):
                return False

        if filters.project_id:
            project_id = metadata.get("project_id")
            if project_id != filters.project_id:
                return False

        return True