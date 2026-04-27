from __future__ import annotations

from pathlib import Path

import pytest

from domain_docs.parsing import CanonicalDocumentParser
from infra.docs.ocr_gateway import SidecarPdfOcrGateway
from scripts.build_binary_demo_documents import build_binary_demo_documents


def test_build_binary_demo_documents_are_parseable(tmp_path: Path) -> None:
    pytest.importorskip("docx")
    pytest.importorskip("fitz")

    written = build_binary_demo_documents(output_dir=tmp_path, overwrite=True)

    assert sorted(Path(path).name for path in written) == [
        "05_release_notes.docx",
        "06_audit_summary.pdf",
        "07_scanned_signoff.pdf",
        "07_scanned_signoff.pdf.ocr.txt",
    ]
    documents = CanonicalDocumentParser(pdf_ocr_gateway=SidecarPdfOcrGateway()).parse_dir(tmp_path)

    assert {document.file_type for document in documents} == {"docx", "pdf"}
    assert all(document.content_blocks for document in documents)
    scanned = next(document for document in documents if document.metadata_profile["file_name"] == "07_scanned_signoff.pdf")
    docx_document = next(document for document in documents if document.metadata_profile["file_name"] == "05_release_notes.docx")
    assert "ocr_applied" in scanned.quality_flags
    assert docx_document.extracted_tables
    assert any(block.block_type == "table_row" for block in docx_document.content_blocks)
    assert docx_document.extracted_tables[0].title == "Approval Matrix"
