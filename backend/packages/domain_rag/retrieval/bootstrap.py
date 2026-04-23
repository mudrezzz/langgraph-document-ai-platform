from __future__ import annotations

from application.canonical_document_service import CanonicalDocumentApplicationService
from domain_rag.retrieval.canonical_dataset import load_canonical_knowledge_dataset
from domain_rag.retrieval.datasets import load_case_dataset
from domain_rag.retrieval.workflows import RetrievalPackWorkflow
from framework.rag.evidence import EvidenceBuilder
from framework.rag.pipeline import HierarchicalRAGPipeline
from framework.rag.reranker import GatewayReranker
from framework.models.interfaces import IEmbeddingGateway
from infra.pgvector.vector_store import PgVectorStoreAdapter
from infra.retrieval.canonical_retrievers import CanonicalVectorRetriever
from infra.retrieval.retrievers import InMemoryRetriever
from infra.tei.rerank_gateway import TeiRerankGateway


def build_retrieval_workflow(
    *,
    case_dataset_id: str | None = None,
    case_dataset_path: str | None = None,
    case_dataset_dir: str | None = None,
    knowledge_source: str | None = None,
    canonical_document_service: CanonicalDocumentApplicationService | None = None,
    canonical_doc_ids: list[str] | None = None,
    embedding_gateway: IEmbeddingGateway | None = None,
    vector_store: PgVectorStoreAdapter | None = None,
    checkpointer: object | None = None,
) -> RetrievalPackWorkflow:
    """Собирает retrieval workflow из concrete adapters и тестового case dataset."""

    if knowledge_source == "canonical":
        if canonical_document_service is None:
            raise ValueError("knowledge_source=canonical требует canonical_document_service")
        summary_blocks, detail_blocks = load_canonical_knowledge_dataset(
            canonical_document_service,
            doc_ids=canonical_doc_ids,
        )
        detail_retriever = (
            CanonicalVectorRetriever(
                embedding_gateway=embedding_gateway,
                vector_store=vector_store,
                doc_ids=canonical_doc_ids,
            )
            if embedding_gateway is not None and vector_store is not None
            else InMemoryRetriever(detail_blocks)
        )
    else:
        summary_blocks, detail_blocks = load_case_dataset(
            dataset_id=case_dataset_id,
            dataset_path=case_dataset_path,
            dataset_dir=case_dataset_dir,
        )
        detail_retriever = InMemoryRetriever(detail_blocks)

    pipeline = HierarchicalRAGPipeline(
        summary_retriever=InMemoryRetriever(summary_blocks),
        detail_retriever=detail_retriever,
        reranker=GatewayReranker(TeiRerankGateway()),
        evidence_builder=EvidenceBuilder(),
    )
    return RetrievalPackWorkflow(pipeline, checkpointer=checkpointer)
