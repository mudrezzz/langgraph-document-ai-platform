"""TEI infrastructure adapters."""

from infra.tei.embedding_gateway import TeiEmbeddingGateway
from infra.tei.rerank_gateway import TeiRerankGateway

__all__ = ["TeiEmbeddingGateway", "TeiRerankGateway"]
