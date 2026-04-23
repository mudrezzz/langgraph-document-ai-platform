from __future__ import annotations

import json
import importlib.util
from pathlib import Path

import pytest

from domain_docs.parsing import CanonicalDocumentParser


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


def test_canonical_parser_parses_release_demo_directory() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    dataset_dir = repo_root / "backend" / "examples" / "cases" / "release_go_no_go_multifile_case" / "input"

    documents = CanonicalDocumentParser().parse_dir(dataset_dir)

    assert len(documents) == 6
    assert {document.file_type for document in documents} == {"docx", "json", "md", "pdf", "txt"}
    assert sum(len(document.content_blocks) for document in documents) >= 8


def test_canonical_parser_reports_missing_docx_dependency_when_needed(tmp_path: Path) -> None:
    if importlib.util.find_spec("docx"):
        pytest.skip("python-docx installed; missing dependency branch is not active")
    source = tmp_path / "sample.docx"
    source.write_bytes(b"not-a-real-docx")

    with pytest.raises(RuntimeError, match="python-docx"):
        CanonicalDocumentParser().parse_path(source)


def test_canonical_parser_reports_missing_pdf_dependency_when_needed(tmp_path: Path) -> None:
    if importlib.util.find_spec("fitz"):
        pytest.skip("PyMuPDF installed; missing dependency branch is not active")
    source = tmp_path / "sample.pdf"
    source.write_bytes(b"%PDF-1.4")

    with pytest.raises(RuntimeError, match="PyMuPDF"):
        CanonicalDocumentParser().parse_path(source)
