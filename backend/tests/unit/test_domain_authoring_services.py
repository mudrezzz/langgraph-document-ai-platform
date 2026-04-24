from __future__ import annotations

from domain_authoring import DocumentAssembler, OutlinePlanner, ResearchSummaryBuilder, SectionReviewService, WriterDraftService
from schemas.rag.contracts import EvidencePack, RerankedBlock, SourceRef


def _build_evidence_pack() -> EvidencePack:
    return EvidencePack(
        selected_sources=[
            SourceRef(doc_id="REQ-1", version="1", block_id="B-1"),
            SourceRef(doc_id="SEC-1", version="1", block_id="B-2"),
            SourceRef(doc_id="REQ-1", version="1", block_id="B-1"),
        ],
        selected_blocks=[
            RerankedBlock(
                text="Critical approval is pending before release.",
                source=SourceRef(doc_id="REQ-1", version="1", block_id="B-1"),
                score=0.9,
                metadata={"document_type": "requirements"},
            ),
            RerankedBlock(
                text="Security governance approval is required.",
                source=SourceRef(doc_id="SEC-1", version="1", block_id="B-2"),
                score=0.8,
                metadata={"document_type": "security"},
            ),
        ],
        unresolved_gaps=[],
        confidence_notes=[],
    )


def test_section_review_service_returns_conditional_go_with_approval_context() -> None:
    service = SectionReviewService()

    result = service.review_draft(
        query="release readiness",
        draft="# Draft",
        evidence_pack=_build_evidence_pack(),
        workflow_mode="multi_step",
    )

    assert result["status"] == "completed"
    assert result["recommendation"] == "conditional_go"
    assert result["risk_count"] == 1
    assert result["approval_mentions"] >= 1


def test_outline_planner_builds_traceability_and_dedups_sources() -> None:
    planner = OutlinePlanner()
    evidence_pack = _build_evidence_pack()
    review_result = {"status": "completed"}

    sections = planner.build_section_traceability(evidence_pack=evidence_pack, review_result=review_result)
    traceability = planner.build_traceability(
        retrieval_task_id="retrieval-1",
        evidence_pack=evidence_pack,
        section_traceability=sections,
        workflow_steps=[{"step": "research", "status": "completed"}],
    )

    assert len(sections) == 4
    assert sections[0]["section_id"] == "risk_assessment"
    assert sections[-1]["section_id"] == "evidence_register"
    assert len(traceability["source_refs"]) == 2
    assert traceability["retrieval_task_id"] == "retrieval-1"


def test_document_assembler_builds_multistep_report() -> None:
    assembler = DocumentAssembler()

    content = assembler.assemble_document(
        query="release readiness",
        research_summary="Research summary",
        writer_draft="Writer draft",
        review_result={
            "status": "completed",
            "recommendation": "conditional_go",
            "notes": "Need final approval.",
            "issues": ["Pending security approval"],
        },
        section_traceability=[
            {
                "section_id": "final_recommendation",
                "title": "Final Recommendation",
                "review_status": "completed",
                "source_refs": [{"doc_id": "REQ-1", "version": "1", "block_id": "B-1"}],
            }
        ],
        workflow_mode="multi_step",
    )

    assert "# Release Readiness Report" in content
    assert "## Reviewer" in content
    assert "Pending security approval" in content


def test_research_summary_builder_formats_evidence_observations() -> None:
    builder = ResearchSummaryBuilder()

    summary = builder.build_summary(query="release readiness", evidence_pack=_build_evidence_pack())

    assert "Запрос:" in summary
    assert "Ключевые наблюдения:" in summary
    assert "REQ-1/B-1" in summary


def test_writer_draft_service_builds_deterministic_draft_and_prompt() -> None:
    service = WriterDraftService()
    evidence_pack = _build_evidence_pack()

    draft = service.build_deterministic_draft(
        query="release readiness",
        evidence_pack=evidence_pack,
        research_summary="Research summary",
    )
    prompt = service.build_llm_prompt(
        query="release readiness",
        evidence_pack=evidence_pack,
        research_summary="Research summary",
    )

    assert "## Writer Draft" in draft
    assert "Critical approval is pending" in draft
    assert "Research summary:" in prompt
    assert "[REQ-1/1/B-1]" in prompt
