from __future__ import annotations

from pathlib import Path

from application.canonical_document_service import CanonicalDocumentApplicationService
from domain_docs.parsing import CanonicalDocumentParser
from infra.postgres.canonical_document_store import PostgresCanonicalDocumentStore


def test_canonical_document_store_fallback_lists_documents_and_blocks(tmp_path: Path) -> None:
    source = tmp_path / "security_findings.md"
    source.write_text("## Security\n\n- Finding one\n- Finding two\n", encoding="utf-8")
    document = CanonicalDocumentParser().parse_path(source)
    service = CanonicalDocumentApplicationService(
        store=PostgresCanonicalDocumentStore(use_fallback_if_unset=True)
    )

    saved_doc_id = service.save_document(document)
    loaded = service.get_document(saved_doc_id)
    documents_page = service.list_documents(limit=10, file_type="md")
    blocks_page = service.list_blocks(limit=10, doc_id=saved_doc_id, block_type="bullet")

    assert loaded.doc_id == saved_doc_id
    assert documents_page.total_returned == 1
    assert blocks_page.total_returned == 2
    assert all(block.doc_id == saved_doc_id for block in blocks_page.items)
    assert loaded.parser_quality.blocks_total == 2


def test_canonical_document_store_replaces_blocks_on_update(tmp_path: Path) -> None:
    source = tmp_path / "ops_readiness.txt"
    source.write_text("First paragraph", encoding="utf-8")
    parser = CanonicalDocumentParser()
    service = CanonicalDocumentApplicationService(
        store=PostgresCanonicalDocumentStore(use_fallback_if_unset=True)
    )

    first = parser.parse_path(source)
    service.save_document(first)
    source.write_text("First paragraph\n\nSecond paragraph", encoding="utf-8")
    second = parser.parse_path(source)
    service.save_document(second)

    blocks_page = service.list_blocks(limit=10, doc_id=second.doc_id)

    assert blocks_page.total_returned == 2
