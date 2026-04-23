from __future__ import annotations

from pathlib import Path

from application.canonical_document_service import CanonicalDocumentApplicationService
from application.knowledge_indexing_service import KnowledgeIndexingApplicationService
from domain_rag.retrieval.canonical_dataset import load_canonical_knowledge_dataset
from infra.postgres.canonical_document_store import PostgresCanonicalDocumentStore


def test_load_canonical_knowledge_dataset_from_indexed_demo_dir() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    dataset_dir = repo_root / "backend" / "examples" / "cases" / "release_go_no_go_multifile_case" / "input"
    canonical_service = CanonicalDocumentApplicationService(
        store=PostgresCanonicalDocumentStore(use_fallback_if_unset=True)
    )
    indexing_service = KnowledgeIndexingApplicationService(canonical_document_service=canonical_service)
    result = indexing_service.index_paths([dataset_dir])

    summary, detail = load_canonical_knowledge_dataset(
        canonical_service,
        doc_ids=result.indexed_doc_ids,
    )

    assert len(summary) >= 3
    assert len(detail) >= 8
    assert all(block.metadata.get("project_id") == "p1" for block in summary + detail)
    assert any(block.metadata.get("block_kind") == "section_summary" for block in summary)
    assert any(block.metadata.get("block_kind") == "content_block" for block in detail)
