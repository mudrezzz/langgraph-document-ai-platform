from __future__ import annotations

from framework.models.interfaces import IChatModelGateway, IEmbeddingGateway, IRerankGateway


class ModelGatewayFactory:
    """Фабрика model gateways."""

    def __init__(self) -> None:
        self._chat_registry: dict[str, type[IChatModelGateway]] = {}
        self._embedding_registry: dict[str, type[IEmbeddingGateway]] = {}
        self._rerank_registry: dict[str, type[IRerankGateway]] = {}

    def register_chat(self, key: str, gateway: type[IChatModelGateway]) -> None:
        self._chat_registry[key] = gateway

    def register_embedding(self, key: str, gateway: type[IEmbeddingGateway]) -> None:
        self._embedding_registry[key] = gateway

    def register_rerank(self, key: str, gateway: type[IRerankGateway]) -> None:
        self._rerank_registry[key] = gateway

    def build_chat(self, key: str) -> IChatModelGateway:
        return self._chat_registry[key]()

    def build_embedding(self, key: str) -> IEmbeddingGateway:
        return self._embedding_registry[key]()

    def build_rerank(self, key: str) -> IRerankGateway:
        return self._rerank_registry[key]()