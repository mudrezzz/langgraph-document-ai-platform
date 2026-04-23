from __future__ import annotations

from application.canonical_document_service import CanonicalDocumentApplicationService
from domain_rag.retrieval.canonical_dataset import load_canonical_knowledge_dataset
from domain_rag.retrieval.datasets import load_case_dataset
from domain_rag.retrieval.workflows import RetrievalPackWorkflow
from framework.rag.evidence import EvidenceBuilder
from framework.rag.pipeline import HierarchicalRAGPipeline
from framework.rag.reranker import GatewayReranker
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
    else:
        summary_blocks, detail_blocks = load_case_dataset(
            dataset_id=case_dataset_id,
            dataset_path=case_dataset_path,
            dataset_dir=case_dataset_dir,
        )

    pipeline = HierarchicalRAGPipeline(
        summary_retriever=InMemoryRetriever(summary_blocks),
        detail_retriever=InMemoryRetriever(detail_blocks),
        reranker=GatewayReranker(TeiRerankGateway()),
        evidence_builder=EvidenceBuilder(),
    )
    return RetrievalPackWorkflow(pipeline, checkpointer=checkpointer)
