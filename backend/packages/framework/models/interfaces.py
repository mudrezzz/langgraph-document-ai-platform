from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class IChatModelGateway(Protocol):
    """Контракт доступа к генеративной модели."""

    def generate(self, prompt: str, *, metadata: dict[str, Any] | None = None) -> str:
        """Выполняет генерацию текста по подготовленному промпту."""


@runtime_checkable
class IEmbeddingGateway(Protocol):
    """Контракт получения векторных представлений."""

    def embed(self, text: str) -> list[float]:
        """Возвращает embedding для входного текста."""


@runtime_checkable
class IRerankGateway(Protocol):
    """Контракт rerank-оценки документов/блоков."""

    def rerank(self, query: str, candidates: list[str]) -> list[float]:
        """Возвращает релевантностные оценки для кандидатов."""
