from __future__ import annotations

import hashlib
import math

from framework.models.interfaces import IEmbeddingGateway


class TeiEmbeddingGateway(IEmbeddingGateway):
    """Скелет gateway embeddings для TEI."""

    def __init__(self, vector_dim: int = 1536) -> None:
        self._vector_dim = vector_dim

    def embed(self, text: str) -> list[float]:
        # Детерминированный hashing-vector для локального контура.
        tokens = text.lower().split()
        vector = [0.0] * self._vector_dim
        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % self._vector_dim
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[index] += sign

        if not tokens:
            return vector

        norm = math.sqrt(sum(value * value for value in vector))
        if norm <= 0:
            return vector
        return [value / norm for value in vector]
