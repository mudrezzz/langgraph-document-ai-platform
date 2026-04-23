from __future__ import annotations

from pathlib import Path

import pytest

from domain_docs.parsing import CanonicalDocumentParser
from scripts.build_binary_demo_documents import build_binary_demo_documents


def test_build_binary_demo_documents_are_parseable(tmp_path: Path) -> None:
    pytest.importorskip("docx")
    pytest.importorskip("fitz")

    written = build_binary_demo_documents(output_dir=tmp_path, overwrite=True)

    assert sorted(Path(path).name for path in written) == ["05_release_notes.docx", "06_audit_summary.pdf"]
    documents = CanonicalDocumentParser().parse_dir(tmp_path)

    assert {document.file_type for document in documents} == {"docx", "pdf"}
    assert all(document.content_blocks for document in documents)
