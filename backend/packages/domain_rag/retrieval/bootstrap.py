from __future__ import annotations

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
    checkpointer: object | None = None,
) -> RetrievalPackWorkflow:
    """Собирает retrieval workflow из concrete adapters и тестового case dataset."""

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
