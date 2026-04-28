from __future__ import annotations

from domain_docs.indexing.quality_policy import KnowledgeIndexingQualityPolicy
from schemas.documents.contracts import (
    CanonicalContentBlock,
    CanonicalDocument,
    ParserQualityIssue,
    ParserQualitySummary,
)


def _document(
    *,
    doc_id: str,
    flags: list[str],
    form_confidence_score: int | None = None,
    ocr_confidence_score: int | None = None,
) -> CanonicalDocument:
    issues = []
    if form_confidence_score is not None:
        issues.append(
            ParserQualityIssue(
                code="pdf_form_like_blocks_detected",
                severity="info",
                message="PDF parser detected form-like key/value layout blocks",
                metadata={"form_confidence_score": form_confidence_score},
            )
        )
    if ocr_confidence_score is not None:
        issues.append(
            ParserQualityIssue(
                code="ocr_applied",
                severity="info",
                message="OCR fallback recovered text for scanned PDF",
                metadata={"ocr_confidence_score": ocr_confidence_score},
            )
        )
    return CanonicalDocument(
        doc_id=doc_id,
        source_path=f"/tmp/{doc_id}.pdf",
        version="1",
        file_type="pdf",
        content_blocks=[CanonicalContentBlock(block_id="B-1", text="placeholder")],
        quality_flags=flags,
        parser_quality=ParserQualitySummary(issues=issues, flags=flags),
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


def test_quality_policy_adds_form_confidence_low_warning_by_threshold() -> None:
    document = _document(
        doc_id="DOC-3",
        flags=["pdf_form_like_blocks_detected"],
        form_confidence_score=62,
    )

    decision = KnowledgeIndexingQualityPolicy(
        form_confidence_min_score=80,
    ).evaluate(
        documents=[document],
        quality_flags=[f"{document.doc_id}:{flag}" for flag in document.quality_flags],
    )

    assert decision.gate_status == "warning"
    assert decision.rejected_documents_total == 0
    assert f"{document.doc_id}:pdf_form_confidence_low" in decision.warning_flags
    assert decision.documents_with_pdf_form_confidence_low == 1
    assert decision.pdf_form_confidence_by_doc[document.doc_id]["score"] == 62
    assert decision.pdf_form_confidence_by_doc[document.doc_id]["threshold"] == 80
    assert decision.pdf_form_confidence_by_doc[document.doc_id]["blocking"] is False


def test_quality_policy_can_block_on_low_form_confidence() -> None:
    document = _document(
        doc_id="DOC-4",
        flags=["pdf_form_like_blocks_detected"],
        form_confidence_score=51,
    )

    decision = KnowledgeIndexingQualityPolicy(
        form_confidence_min_score=75,
        form_confidence_low_blocking=True,
    ).evaluate(
        documents=[document],
        quality_flags=[f"{document.doc_id}:{flag}" for flag in document.quality_flags],
    )

    assert decision.gate_status == "failed"
    assert decision.rejected_documents_total == 1
    assert f"{document.doc_id}:pdf_form_confidence_low" in decision.blocking_flags


def test_quality_policy_adds_ocr_confidence_low_warning_by_threshold() -> None:
    document = _document(
        doc_id="DOC-5",
        flags=["ocr_applied"],
        ocr_confidence_score=41,
    )

    decision = KnowledgeIndexingQualityPolicy(
        ocr_confidence_min_score=70,
    ).evaluate(
        documents=[document],
        quality_flags=[f"{document.doc_id}:{flag}" for flag in document.quality_flags],
    )

    assert decision.gate_status == "warning"
    assert decision.rejected_documents_total == 0
    assert f"{document.doc_id}:ocr_confidence_low" in decision.warning_flags
    assert decision.documents_with_ocr_confidence_low == 1
    assert decision.ocr_confidence_by_doc[document.doc_id]["score"] == 41
    assert decision.ocr_confidence_by_doc[document.doc_id]["threshold"] == 70
    assert decision.ocr_confidence_by_doc[document.doc_id]["blocking"] is False


def test_quality_policy_can_block_on_low_ocr_confidence() -> None:
    document = _document(
        doc_id="DOC-6",
        flags=["ocr_applied"],
        ocr_confidence_score=22,
    )

    decision = KnowledgeIndexingQualityPolicy(
        ocr_confidence_min_score=60,
        ocr_confidence_low_blocking=True,
    ).evaluate(
        documents=[document],
        quality_flags=[f"{document.doc_id}:{flag}" for flag in document.quality_flags],
    )

    assert decision.gate_status == "failed"
    assert decision.rejected_documents_total == 1
    assert f"{document.doc_id}:ocr_confidence_low" in decision.blocking_flags
