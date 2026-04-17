from __future__ import annotations

from domain_rag.retrieval.workflows import RetrievalPackWorkflow
from framework.rag.evidence import EvidenceBuilder
from framework.rag.pipeline import HierarchicalRAGPipeline
from framework.rag.reranker import GatewayReranker
from infra.retrieval.retrievers import InMemoryRetriever
from infra.tei.rerank_gateway import TeiRerankGateway
from schemas.rag.contracts import RetrievedBlock, SourceRef


def build_retrieval_workflow() -> RetrievalPackWorkflow:
    """Собирает workflow из concrete adapters для локального запуска."""

    summary_blocks = [
        RetrievedBlock(
            text="Проект использует LangGraph для оркестрации",
            source=SourceRef(doc_id="m1", version="1", block_id="s1"),
            score=0.0,
            metadata={"document_type": "methodology", "tags": ["langgraph"], "project_id": "p1"},
        )
    ]

    detail_blocks = [
        RetrievedBlock(
            text="В документе есть требования к evidence pack и rerank",
            source=SourceRef(doc_id="d1", version="2", block_id="b1"),
            score=0.0,
            metadata={"document_type": "requirements", "tags": ["retrieval", "evidence"], "project_id": "p1"},
        ),
        RetrievedBlock(
            text="Система поддерживает interrupt resume и checkpoint",
            source=SourceRef(doc_id="d2", version="1", block_id="b2"),
            score=0.0,
            metadata={"document_type": "requirements", "tags": ["hitl"], "project_id": "p1"},
        ),
    ]

    pipeline = HierarchicalRAGPipeline(
        summary_retriever=InMemoryRetriever(summary_blocks),
        detail_retriever=InMemoryRetriever(detail_blocks),
        reranker=GatewayReranker(TeiRerankGateway()),
        evidence_builder=EvidenceBuilder(),
    )
    return RetrievalPackWorkflow(pipeline)