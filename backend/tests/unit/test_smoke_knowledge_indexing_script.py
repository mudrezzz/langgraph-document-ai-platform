from __future__ import annotations

import json
from pathlib import Path

from schemas.documents.contracts import (
    CanonicalContentBlock,
    CanonicalDocument,
    CanonicalSectionSummary,
    CanonicalStructureNode,
    ParserQualitySummary,
)
from scripts import smoke_knowledge_indexing


class _FakeKnowledgeIndexingService:
    def __init__(self, result: object) -> None:
        self._result = result
        self.calls: list[tuple[list[Path], dict]] = []

    def index_paths(self, paths: list[Path], *, task_context: dict | None = None) -> object:
        self.calls.append((paths, task_context or {}))
        return self._result


class _FakeCanonicalDocumentService:
    def list_blocks(self, *, limit: int, doc_id: str | None = None):
        total = 44 if doc_id is None else 2
        return type("_BlocksResult", (), {"total_returned": total})()


class _FakeContainer:
    def __init__(self, result: object) -> None:
        self.knowledge_indexing_service = _FakeKnowledgeIndexingService(result)
        self.canonical_document_service = _FakeCanonicalDocumentService()


def test_smoke_knowledge_indexing_uses_container_managed_service(monkeypatch, capsys) -> None:
    scanned = CanonicalDocument(
        doc_id="07SCANNE-5225",
        source_path="input/07_scanned_signoff.pdf",
        version="1",
        file_type="pdf",
        structure_tree=CanonicalStructureNode(node_id="root", title="PDF Document", level=0),
        content_blocks=[
            CanonicalContentBlock(
                block_id="b1",
                block_type="paragraph",
                text="Scanned Sign-off Record",
                metadata={"ocr_provider": "sidecar", "extraction_mode": "ocr"},
            )
        ],
        section_summaries=[
            CanonicalSectionSummary(section_id="s1", title="Page 1", summary="Recovered by OCR", source_block_ids=["b1"])
        ],
        parser_quality=ParserQualitySummary(
            parser_family="pdf",
            extraction_mode="page_text",
            pages_total=1,
            blocks_total=1,
            issues=[],
            flags=["pdf_no_extractable_text", "ocr_required", "ocr_applied", "ocr_provider:sidecar"],
        ),
        quality_flags=["pdf_no_extractable_text", "ocr_required", "ocr_applied", "ocr_provider:sidecar"],
    )
    result = type(
        "_Result",
        (),
        {
            "documents": [scanned],
            "indexed_doc_ids": ["07SCANNE-5225"],
            "quality_flags": ["07SCANNE-5225:ocr_required", "07SCANNE-5225:ocr_applied"],
            "embeddings_indexed": 2,
            "quality_summary": {"gate_status": "warning", "documents_total": 1},
        },
    )()
    fake_container = _FakeContainer(result)

    monkeypatch.setattr(smoke_knowledge_indexing, "ApiContainer", lambda: fake_container)
    monkeypatch.setattr(smoke_knowledge_indexing, "build_binary_demo_documents", lambda output_dir: [])
    monkeypatch.setattr(
        "sys.argv",
        ["smoke_knowledge_indexing.py", "--input-path", "demo/input", "--build-binary-demo-docs"],
    )

    smoke_knowledge_indexing.main()

    output = json.loads(capsys.readouterr().out)
    assert fake_container.knowledge_indexing_service.calls == [([Path("demo/input")], {"smoke": "knowledge_indexing"})]
    assert output["ocr_recovered_doc_ids"] == ["07SCANNE-5225"]
    assert output["quality_flags"] == ["07SCANNE-5225:ocr_required", "07SCANNE-5225:ocr_applied"]

