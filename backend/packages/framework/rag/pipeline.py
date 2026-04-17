from __future__ import annotations

from abc import ABC

from framework.rag.interfaces import IEvidenceBuilder, IReranker, IRetriever
from schemas.rag.contracts import EvidencePack, RetrievalFilter, RetrievalTrace


class BaseRetrievalPipeline(ABC):
    """Базовый конвейер иерархического retrieval."""

    def __init__(
        self,
        summary_retriever: IRetriever,
        detail_retriever: IRetriever,
        reranker: IReranker,
        evidence_builder: IEvidenceBuilder,
    ) -> None:
        self._summary_retriever = summary_retriever
        self._detail_retriever = detail_retriever
        self._reranker = reranker
        self._evidence_builder = evidence_builder

    def run_with_trace(self, query: str, filters: RetrievalFilter) -> RetrievalTrace:
        # Шаг 1: быстрый отбор по summary-слою.
        summary_candidates = self._summary_retriever.retrieve(query, filters)
        # Шаг 2: углубленный retrieval по детальным блокам.
        detail_candidates = self._detail_retriever.retrieve(query, filters)
        candidates = summary_candidates + detail_candidates
        # Шаг 3: rerank объединенного списка кандидатов.
        reranked = self._reranker.rerank(query, candidates)
        # Шаг 4: сборка evidence pack как стандартизованного артефакта.
        evidence_pack = self._evidence_builder.build(reranked)
        return RetrievalTrace(
            summary_candidates=summary_candidates,
            detail_candidates=detail_candidates,
            reranked_blocks=reranked,
            evidence_pack=evidence_pack,
        )

    def run(self, query: str, filters: RetrievalFilter) -> EvidencePack:
        return self.run_with_trace(query, filters).evidence_pack


class HierarchicalRAGPipeline(BaseRetrievalPipeline):
    """Конкретная реализация базового конвейера для product-пайплайнов."""