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
    assert all(block.is_latest is True for block in blocks_page.items)
    assert loaded.parser_quality.blocks_total == 2


def test_canonical_document_store_preserves_versions_and_latest_read_model(tmp_path: Path) -> None:
    source = tmp_path / "ops_readiness.txt"
    source.write_text("First paragraph", encoding="utf-8")
    parser = CanonicalDocumentParser()
    service = CanonicalDocumentApplicationService(
        store=PostgresCanonicalDocumentStore(use_fallback_if_unset=True)
    )

    first = parser.parse_path(source, version="1")
    service.save_document(first)
    source.write_text("First paragraph\n\nSecond paragraph", encoding="utf-8")
    second = parser.parse_path(source, version="2")
    service.save_document(second)

    latest = service.get_document(second.doc_id)
    explicit_v1 = service.get_document(second.doc_id, version="1")
    documents_page = service.list_documents(limit=10)
    versions_page = service.list_versions(second.doc_id, limit=10)
    latest_blocks = service.list_blocks(limit=10, doc_id=second.doc_id)
    versioned_blocks = service.list_blocks(limit=10, doc_id=second.doc_id, version="1")

    assert latest.version == "2"
    assert len(latest.content_blocks) == 2
    assert explicit_v1.version == "1"
    assert len(explicit_v1.content_blocks) == 1
    assert documents_page.total_returned == 1
    assert documents_page.items[0].version == "2"
    assert versions_page.total_returned == 2
    assert [item.version for item in versions_page.items] == ["2", "1"]
    assert versions_page.items[0].is_latest is True
    assert versions_page.items[1].is_latest is False
    assert latest_blocks.total_returned == 2
    assert all(item.version == "2" for item in latest_blocks.items)
    assert all(item.is_latest is True for item in latest_blocks.items)
    assert versioned_blocks.total_returned == 1
    assert versioned_blocks.items[0].version == "1"
    assert versioned_blocks.items[0].is_latest is False
