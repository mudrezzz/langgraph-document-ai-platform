from __future__ import annotations

from pathlib import Path

import pytest

from domain_docs.parsing import CanonicalDocumentParser
from infra.docs.ocr_gateway import SidecarPdfOcrGateway
from scripts.build_binary_demo_documents import build_binary_demo_documents


def test_build_binary_demo_documents_are_parseable(tmp_path: Path) -> None:
    pytest.importorskip("docx")
    pytest.importorskip("fitz")
    pytest.importorskip("openpyxl")
    pytest.importorskip("pptx")

    written = build_binary_demo_documents(output_dir=tmp_path, overwrite=True)

    assert sorted(Path(path).name for path in written) == [
        "05_release_notes.docx",
        "06_audit_summary.pdf",
        "07_scanned_signoff.pdf",
        "07_scanned_signoff.pdf.ocr.txt",
        "08_release_tracker.xlsx",
        "09_release_briefing.pptx",
    ]
    documents = CanonicalDocumentParser(pdf_ocr_gateway=SidecarPdfOcrGateway()).parse_dir(tmp_path)

    assert {document.file_type for document in documents} == {"docx", "pdf", "xlsx", "pptx"}
    assert all(document.content_blocks for document in documents)
    scanned = next(document for document in documents if document.metadata_profile["file_name"] == "07_scanned_signoff.pdf")
    docx_document = next(document for document in documents if document.metadata_profile["file_name"] == "05_release_notes.docx")
    pdf_document = next(document for document in documents if document.metadata_profile["file_name"] == "06_audit_summary.pdf")
    xlsx_document = next(document for document in documents if document.metadata_profile["file_name"] == "08_release_tracker.xlsx")
    pptx_document = next(document for document in documents if document.metadata_profile["file_name"] == "09_release_briefing.pptx")
    assert "ocr_applied" in scanned.quality_flags
    assert docx_document.extracted_tables
    assert any(block.block_type == "table_row" for block in docx_document.content_blocks)
    assert docx_document.extracted_tables[0].title == "Approval Matrix"
    assert pdf_document.extracted_tables
    assert "pdf_tables_extracted" in pdf_document.quality_flags
    assert "pdf_form_like_blocks_detected" in pdf_document.quality_flags
    assert "pdf_table_extraction_partial" not in pdf_document.quality_flags
    assert "pdf_rotated_layout_detected" in pdf_document.quality_flags
    assert any(block.block_type == "table_row" for block in pdf_document.content_blocks)
    assert any(block.metadata.get("pdf_table_kind") == "form_like" for block in pdf_document.content_blocks)
    assert any(bool(block.metadata.get("rotated_text")) for block in pdf_document.content_blocks)
    form_issue = next(item for item in pdf_document.parser_quality.issues if item.code == "pdf_form_like_blocks_detected")
    assert form_issue.metadata["key_value_pairs_total"] >= 3
    assert form_issue.metadata["key_value_pairs_extracted"] >= 3
    assert form_issue.metadata["form_confidence_score"] > 0
    form_table = next(
        table
        for table in pdf_document.extracted_tables
        if table.metadata.get("pdf_table_kind") == "form_like" and "Decision Rationale" in table.columns
    )
    assert "Decision Rationale" in form_table.columns
    assert xlsx_document.extracted_tables
    assert xlsx_document.parser_quality.parser_family == "xlsx"
    assert any(block.block_type == "table_row" for block in xlsx_document.content_blocks)
    assert pptx_document.parser_quality.parser_family == "pptx"
    assert any(block.block_type == "slide_title" for block in pptx_document.content_blocks)
