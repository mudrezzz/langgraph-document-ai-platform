from __future__ import annotations

from framework.models.interfaces import IRerankGateway


class TeiRerankGateway(IRerankGateway):
    """Скелет rerank gateway для TEI endpoint."""

    def rerank(self, query: str, candidates: list[str]) -> list[float]:
        # Детерминированный скоринг по пересечению токенов запроса и кандидата.
        query_tokens = set(query.lower().split())
        scores: list[float] = []
        for candidate in candidates:
            candidate_tokens = set(candidate.lower().split())
            overlap = len(query_tokens.intersection(candidate_tokens))
            denom = max(len(query_tokens), 1)
            scores.append(float(overlap) / float(denom))
        return scores