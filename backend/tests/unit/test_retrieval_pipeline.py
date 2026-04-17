from framework.rag.evidence import EvidenceBuilder
from framework.rag.pipeline import HierarchicalRAGPipeline
from framework.rag.reranker import GatewayReranker
from infra.retrieval.retrievers import InMemoryRetriever
from infra.tei.rerank_gateway import TeiRerankGateway
from schemas.rag.contracts import RetrievedBlock, RetrievalFilter, SourceRef


def _block(text: str, doc_id: str, tags: list[str]) -> RetrievedBlock:
    return RetrievedBlock(
        text=text,
        source=SourceRef(doc_id=doc_id, version="1", block_id=f"{doc_id}-b"),
        score=0.0,
        metadata={"document_type": "requirements", "tags": tags, "project_id": "p1"},
    )


def test_hierarchical_pipeline_returns_trace_and_evidence() -> None:
    summary = [_block("langgraph orchestration", "s1", ["langgraph"])]
    detail = [
        _block("evidence pack construction", "d1", ["retrieval"]),
        _block("hitl review flow", "d2", ["hitl"]),
    ]

    pipeline = HierarchicalRAGPipeline(
        summary_retriever=InMemoryRetriever(summary),
        detail_retriever=InMemoryRetriever(detail),
        reranker=GatewayReranker(TeiRerankGateway()),
        evidence_builder=EvidenceBuilder(),
    )

    trace = pipeline.run_with_trace("evidence retrieval", RetrievalFilter(project_id="p1"))

    assert len(trace.summary_candidates) == 1
    assert len(trace.detail_candidates) == 2
    assert len(trace.reranked_blocks) == 3
    assert len(trace.evidence_pack.selected_blocks) == 3