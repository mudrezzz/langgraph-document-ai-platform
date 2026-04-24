from __future__ import annotations

from infra.pgvector.vector_store import PgVectorStoreAdapter
from infra.retrieval.canonical_retrievers import CanonicalSummaryVectorRetriever, CanonicalVectorRetriever
from infra.tei.embedding_gateway import TeiEmbeddingGateway
from schemas.rag.contracts import RetrievalFilter


def test_canonical_vector_retriever_returns_vector_ranked_blocks() -> None:
    gateway = TeiEmbeddingGateway(vector_dim=16)
    vector_store = PgVectorStoreAdapter(use_fallback_if_unset=True)
    vector_store.upsert_vector(
        "knowledge_block:DOC-1:1:B-1",
        gateway.embed("security approval pending"),
        {
            "kind": "knowledge_block_embedding",
            "block_ref": "DOC-1:1:B-1",
            "doc_id": "DOC-1",
            "version": "1",
            "block_id": "B-1",
            "block_type": "bullet",
            "text": "security approval pending",
            "project_id": "p1",
            "document_type": "security",
            "tags": ["security"],
        },
    )
    vector_store.upsert_vector(
        "knowledge_block:DOC-2:1:B-1",
        gateway.embed("operations dashboard ready"),
        {
            "kind": "knowledge_block_embedding",
            "block_ref": "DOC-2:1:B-1",
            "doc_id": "DOC-2",
            "version": "1",
            "block_id": "B-1",
            "block_type": "paragraph",
            "text": "operations dashboard ready",
            "project_id": "p1",
            "document_type": "operations",
            "tags": ["ops"],
        },
    )

    retriever = CanonicalVectorRetriever(embedding_gateway=gateway, vector_store=vector_store)
    results = retriever.retrieve(
        "security approval",
        RetrievalFilter(project_id="p1", document_types=["security"]),
    )

    assert len(results) == 1
    assert results[0].source.doc_id == "DOC-1"
    assert results[0].metadata["retrieval_backend"] == "pgvector"


def test_canonical_vector_retriever_limits_results_to_allowed_doc_ids() -> None:
    gateway = TeiEmbeddingGateway(vector_dim=16)
    vector_store = PgVectorStoreAdapter(use_fallback_if_unset=True)
    for doc_id in ["DOC-1", "DOC-OLD"]:
        vector_store.upsert_vector(
            f"knowledge_block:{doc_id}:1:B-1",
            gateway.embed("security approval pending"),
            {
                "kind": "knowledge_block_embedding",
                "block_ref": f"{doc_id}:1:B-1",
                "doc_id": doc_id,
                "version": "1",
                "block_id": "B-1",
                "block_type": "bullet",
                "text": "security approval pending",
                "project_id": "p1",
                "document_type": "security",
                "tags": ["security"],
            },
        )

    retriever = CanonicalVectorRetriever(
        embedding_gateway=gateway,
        vector_store=vector_store,
        doc_ids=["DOC-1"],
    )
    results = retriever.retrieve(
        "security approval",
        RetrievalFilter(project_id="p1", document_types=["security"]),
    )

    assert {result.source.doc_id for result in results} == {"DOC-1"}


def test_canonical_summary_vector_retriever_returns_section_summaries() -> None:
    gateway = TeiEmbeddingGateway(vector_dim=16)
    vector_store = PgVectorStoreAdapter(use_fallback_if_unset=True)
    vector_store.upsert_vector(
        "knowledge_summary:DOC-1:1:summary:SEC-1",
        gateway.embed("release decision depends on security approval"),
        {
            "kind": "knowledge_summary_embedding",
            "block_ref": "DOC-1:1:summary:SEC-1",
            "doc_id": "DOC-1",
            "version": "1",
            "block_id": "summary:SEC-1",
            "section_id": "SEC-1",
            "section_title": "Release Decision",
            "source_block_ids": ["B-1", "B-2"],
            "text": "release decision depends on security approval",
            "project_id": "p1",
            "document_type": "release",
            "tags": ["release"],
        },
    )
    vector_store.upsert_vector(
        "knowledge_block:DOC-1:1:B-1",
        gateway.embed("release decision depends on security approval"),
        {
            "kind": "knowledge_block_embedding",
            "block_ref": "DOC-1:1:B-1",
            "doc_id": "DOC-1",
            "version": "1",
            "block_id": "B-1",
            "text": "release decision depends on security approval",
            "project_id": "p1",
            "document_type": "release",
            "tags": ["release"],
        },
    )

    retriever = CanonicalSummaryVectorRetriever(embedding_gateway=gateway, vector_store=vector_store)
    results = retriever.retrieve("security approval", RetrievalFilter(project_id="p1"))

    assert len(results) == 1
    assert results[0].source.block_id == "summary:SEC-1"
    assert results[0].metadata["block_kind"] == "section_summary"
    assert results[0].metadata["section_title"] == "Release Decision"
    assert results[0].metadata["source_block_ids"] == ["B-1", "B-2"]
