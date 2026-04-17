from __future__ import annotations

from framework.models.interfaces import IRerankGateway
from framework.rag.interfaces import IReranker
from schemas.rag.contracts import RerankedBlock, RetrievedBlock


class GatewayReranker(IReranker):
    """Reranker, использующий модельный gateway для пересчета релевантности."""

    def __init__(self, gateway: IRerankGateway) -> None:
        self._gateway = gateway

    def rerank(self, query: str, candidates: list[RetrievedBlock]) -> list[RerankedBlock]:
        texts = [candidate.text for candidate in candidates]
        scores = self._gateway.rerank(query, texts)

        reranked = [
            RerankedBlock(
                text=candidate.text,
                source=candidate.source,
                score=score,
                metadata=candidate.metadata,
            )
            for candidate, score in zip(candidates, scores, strict=False)
        ]

        return sorted(reranked, key=lambda item: item.score, reverse=True)