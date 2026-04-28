from __future__ import annotations

from domain_docs.indexing.quality_policy import KnowledgeIndexingQualityPolicy
from schemas.documents.contracts import CanonicalContentBlock, CanonicalDocument


def _document(*, doc_id: str, flags: list[str]) -> CanonicalDocument:
    return CanonicalDocument(
        doc_id=doc_id,
        source_path=f"/tmp/{doc_id}.pdf",
        version="1",
        file_type="pdf",
        content_blocks=[CanonicalContentBlock(block_id="B-1", text="placeholder")],
        quality_flags=flags,
    )


def test_quality_policy_treats_recovered_ocr_as_warning() -> None:
    document = _document(
        doc_id="DOC-1",
        flags=["pdf_no_extractable_text", "ocr_required", "ocr_applied"],
    )

    decision = KnowledgeIndexingQualityPolicy().evaluate(
        documents=[document],
        quality_flags=[f"{document.doc_id}:{flag}" for flag in document.quality_flags],
    )

    assert decision.gate_status == "warning"
    assert decision.rejected_documents_total == 0
    assert f"{document.doc_id}:pdf_no_extractable_text" in decision.warning_flags


def test_quality_policy_can_force_warning_for_blocking_flag() -> None:
    document = _document(
        doc_id="DOC-2",
        flags=["empty_document", "no_content_blocks"],
    )

    decision = KnowledgeIndexingQualityPolicy(
        warning_only_flags={"empty_document"},
    ).evaluate(
        documents=[document],
        quality_flags=[f"{document.doc_id}:{flag}" for flag in document.quality_flags],
    )

    assert decision.gate_status == "failed"
    assert decision.rejected_documents_total == 1
    assert f"{document.doc_id}:empty_document" in decision.warning_flags
    assert f"{document.doc_id}:no_content_blocks" in decision.blocking_flags
