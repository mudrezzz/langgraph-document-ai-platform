from __future__ import annotations

from framework.models.interfaces import IEmbeddingGateway


class TeiEmbeddingGateway(IEmbeddingGateway):
    """Скелет gateway embeddings для TEI."""

    def embed(self, text: str) -> list[float]:
        # Простая детерминированная заглушка вектора для тестового контура.
        tokens = text.lower().split()
        return [float(len(tokens)), float(len(text))]