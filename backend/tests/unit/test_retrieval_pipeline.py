from framework.rag.evidence import EvidenceBuilder, RetrievalQualityPolicy
from framework.rag.pipeline import HierarchicalRAGPipeline
from framework.rag.reranker import GatewayReranker
from infra.retrieval.retrievers import InMemoryRetriever
from infra.tei.rerank_gateway import TeiRerankGateway
from schemas.rag.contracts import RerankedBlock, RetrievedBlock, RetrievalFilter, SourceRef


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


def test_evidence_builder_adds_quality_gaps_and_confidence_notes() -> None:
    reranked = [
        RerankedBlock(
            text="security approval pending",
            source=SourceRef(doc_id="SEC-1", version="1", block_id="SEC-1-b"),
            score=0.1,
            metadata={"document_type": "security", "tags": ["security"], "project_id": "p1"},
        )
    ]
    pack = EvidenceBuilder(
        RetrievalQualityPolicy(
            min_evidence_count=2,
            min_confidence_score=0.5,
            required_document_types=("methodology",),
        )
    ).build(reranked)

    assert any(gap.startswith("low_evidence_count") for gap in pack.unresolved_gaps)
    assert any(gap.startswith("low_confidence") for gap in pack.unresolved_gaps)
    assert "missing_required_document_types: methodology" in pack.unresolved_gaps
    assert pack.confidence_notes == ["top_confidence=0.100"]


def test_evidence_builder_detects_missing_source_refs() -> None:
    pack = EvidenceBuilder().build(
        [
            RerankedBlock(
                text="orphan evidence",
                source=SourceRef(doc_id="", version="1", block_id=""),
                score=0.8,
                metadata={"document_type": "methodology"},
            )
        ]
    )

    assert "missing_source_refs: 1 blocks" in pack.unresolved_gaps
