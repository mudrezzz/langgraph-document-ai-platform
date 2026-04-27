from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from domain_docs.parsing import CanonicalDocumentParser
from infra.docs.ocr_gateway import SidecarPdfOcrGateway
from scripts.build_binary_demo_documents import build_binary_demo_documents


def test_canonical_parser_extracts_markdown_structure(tmp_path: Path) -> None:
    source = tmp_path / "release_decision.md"
    source.write_text(
        "# Release\n\n## Decision\n\n- GO is blocked by pending approval\n- Security review is required\n",
        encoding="utf-8",
    )

    document = CanonicalDocumentParser().parse_path(source)

    assert document.file_type == "md"
    assert document.metadata_profile["document_type"] == "methodology"
    assert len(document.content_blocks) == 2
    assert document.content_blocks[0].block_type == "bullet"
    assert document.content_blocks[0].heading_path == ["Release", "Decision"]
    assert len(document.section_summaries) >= 1
    assert document.parser_quality.parser_family == "markdown"
    assert document.parser_quality.headings_total == 2
    assert document.parser_quality.lists_total == 2
    assert document.parser_quality.blocks_total == 2


def test_canonical_parser_extracts_json_values(tmp_path: Path) -> None:
    source = tmp_path / "approvals.json"
    source.write_text(
        json.dumps({"security": {"status": "PENDING"}, "approvers": ["SRE", "Risk"]}),
        encoding="utf-8",
    )

    document = CanonicalDocumentParser().parse_path(source)

    assert document.file_type == "json"
    assert document.metadata_profile["document_type"] == "governance"
    assert len(document.content_blocks) == 3
    assert any("security.status: PENDING" in block.text for block in document.content_blocks)
    assert document.quality_flags == []
    assert document.parser_quality.parser_family == "json"
    assert document.parser_quality.extraction_mode == "structured"
    assert document.parser_quality.issues == []


def test_canonical_parser_doc_id_is_stable_for_relative_and_absolute_paths(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_dir = tmp_path / "docs"
    source_dir.mkdir()
    source = source_dir / "release_decision.md"
    source.write_text("# Release\n\nGO is blocked by pending approval.", encoding="utf-8")

    parser = CanonicalDocumentParser()
    monkeypatch.chdir(tmp_path)

    relative_document = parser.parse_path(Path("docs") / "release_decision.md")
    absolute_document = parser.parse_path(source.resolve())

    assert relative_document.doc_id == absolute_document.doc_id


def test_canonical_parser_parses_release_demo_directory() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    dataset_dir = repo_root / "backend" / "examples" / "cases" / "release_go_no_go_multifile_case" / "input"
    build_binary_demo_documents(output_dir=dataset_dir, overwrite=True)

    documents = CanonicalDocumentParser(pdf_ocr_gateway=SidecarPdfOcrGateway()).parse_dir(dataset_dir)

    assert len(documents) == 7
    assert {document.file_type for document in documents} == {"docx", "json", "md", "pdf", "txt"}
    assert sum(len(document.content_blocks) for document in documents) >= 8
    assert any(document.parser_quality.parser_family == "docx" for document in documents)
    assert any(document.parser_quality.parser_family == "pdf" for document in documents)


def test_canonical_parser_reports_docx_table_quality_flags(tmp_path: Path) -> None:
    pytest.importorskip("docx")
    from docx import Document

    source = tmp_path / "release_notes.docx"
    document = Document()
    document.add_heading("Release Notes", level=1)
    table = document.add_table(rows=2, cols=2)
    table.cell(0, 0).text = "Check"
    table.cell(0, 1).text = "Status"
    table.cell(1, 0).text = "Security sign-off"
    table.cell(1, 1).text = "Pending"
    document.save(source)

    parsed = CanonicalDocumentParser().parse_path(source)

    assert "docx_tables_detected" in parsed.quality_flags
    assert parsed.parser_quality.tables_total == 1
    assert len(parsed.extracted_tables) == 1
    assert parsed.extracted_tables[0].columns == ["Check", "Status"]
    assert parsed.extracted_tables[0].rows[0]["Check"] == "Security sign-off"
    assert any(block.block_type == "table_row" for block in parsed.content_blocks)


def test_canonical_parser_detects_docx_lists_and_appendix(tmp_path: Path) -> None:
    pytest.importorskip("docx")
    from docx import Document

    source = tmp_path / "appendix_notes.docx"
    document = Document()
    document.add_heading("Main", level=1)
    document.add_paragraph("1. Review rollout", style="List Number")
    document.add_heading("Appendix A: Contacts", level=2)
    document.add_paragraph("Primary: sre@example.com")
    document.save(source)

    parsed = CanonicalDocumentParser().parse_path(source)

    assert parsed.parser_quality.lists_total >= 1
    assert "appendix_section_detected" in parsed.quality_flags
    assert any(block.block_type == "bullet" for block in parsed.content_blocks)


def test_canonical_parser_reports_empty_pdf_as_ocr_candidate(tmp_path: Path) -> None:
    pytest.importorskip("fitz")
    import fitz

    source = tmp_path / "scan.pdf"
    pdf = fitz.open()
    pdf.new_page()
    pdf.save(source)
    pdf.close()

    parsed = CanonicalDocumentParser().parse_path(source)

    assert "pdf_no_extractable_text" in parsed.quality_flags
    assert "ocr_required" in parsed.quality_flags
    assert "ocr_not_available" in parsed.quality_flags
    assert parsed.parser_quality.parser_family == "pdf"
    assert parsed.parser_quality.pages_total == 1
    assert any(issue.code == "ocr_required" for issue in parsed.parser_quality.issues)


def test_canonical_parser_uses_sidecar_ocr_for_scanned_pdf(tmp_path: Path) -> None:
    pytest.importorskip("fitz")
    import fitz

    source = tmp_path / "scan.pdf"
    pdf = fitz.open()
    pdf.new_page()
    pdf.save(source)
    pdf.close()
    source.with_suffix(".pdf.ocr.txt").write_text(
        "Recovered sign-off via OCR\n\nOperations readiness approved.",
        encoding="utf-8",
    )

    parsed = CanonicalDocumentParser(pdf_ocr_gateway=SidecarPdfOcrGateway()).parse_path(source)

    assert "ocr_required" in parsed.quality_flags
    assert "ocr_applied" in parsed.quality_flags
    assert "ocr_provider:sidecar" in parsed.quality_flags
    assert parsed.content_blocks
    assert parsed.content_blocks[0].metadata["ocr_provider"] == "sidecar"
    assert any(issue.code == "ocr_applied" for issue in parsed.parser_quality.issues)


def test_canonical_parser_reports_missing_docx_dependency_when_needed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_import = __import__

    def fake_import(name: str, *args: Any, **kwargs: Any) -> Any:
        if name == "docx":
            raise ImportError("docx unavailable")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr("builtins.__import__", fake_import)
    source = tmp_path / "sample.docx"
    source.write_bytes(b"not-a-real-docx")

    with pytest.raises(RuntimeError, match="python-docx"):
        CanonicalDocumentParser().parse_path(source)


def test_canonical_parser_reports_missing_pdf_dependency_when_needed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_import = __import__

    def fake_import(name: str, *args: Any, **kwargs: Any) -> Any:
        if name == "fitz":
            raise ImportError("fitz unavailable")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr("builtins.__import__", fake_import)
    source = tmp_path / "sample.pdf"
    source.write_bytes(b"%PDF-1.4")

    with pytest.raises(RuntimeError, match="PyMuPDF"):
        CanonicalDocumentParser().parse_path(source)
