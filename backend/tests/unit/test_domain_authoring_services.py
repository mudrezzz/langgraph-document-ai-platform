from __future__ import annotations

from domain_docs import TemplateCompiler
from domain_authoring import (
    ArtifactExporter,
    DocumentAssembler,
    DocumentAssemblyWorkflow,
    OutlinePlanner,
    ResearchSummaryBuilder,
    SectionAuthoringService,
    SectionAuthoringWorkflow,
    SectionContractBuilder,
    SectionReviewService,
    WriterDraftService,
)
from schemas.authoring.contracts import SectionPacket
from schemas.rag.contracts import EvidencePack, RerankedBlock, SourceRef
from schemas.workflow.states import SectionAuthoringState


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


def test_outline_planner_builds_outline_snapshot() -> None:
    planner = OutlinePlanner()
    evidence_pack = _build_evidence_pack()
    review_result = {"status": "completed"}
    builder = SectionContractBuilder()
    contracts = builder.build_release_readiness_contracts(
        evidence_pack=evidence_pack,
        review_status="completed",
    )

    snapshot = planner.build_outline_snapshot(
        template_id="release_readiness",
        section_contracts=contracts,
        section_traceability=planner.build_section_traceability(
            evidence_pack=evidence_pack,
            review_result=review_result,
        ),
    )

    assert snapshot["template_id"] == "release_readiness"
    assert snapshot["sections"][0]["section_id"] == "risk_assessment"
    assert snapshot["sections"][0]["objective"]
    assert snapshot["sections"][0]["source_refs"]


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

    source_refs = planner.collect_source_refs_from_sections(sections)
    normalized_refs = planner.to_source_refs(traceability["source_refs"])
    assert len(source_refs) == 2
    assert normalized_refs[0].doc_id == "REQ-1"


def test_section_contract_builder_builds_release_readiness_contracts() -> None:
    builder = SectionContractBuilder()

    contracts = builder.build_release_readiness_contracts(
        evidence_pack=_build_evidence_pack(),
        review_status="completed",
    )

    assert len(contracts) == 4
    assert contracts[0].section_id == "risk_assessment"
    assert contracts[1].section_id == "pending_approvals"
    assert contracts[-1].metadata["review_status"] == "informational"
    assert contracts[0].preferred_source_refs


def test_section_packet_is_typed_and_preserves_context() -> None:
    builder = SectionContractBuilder()
    contract = builder.build_release_readiness_contracts(
        evidence_pack=_build_evidence_pack(),
        review_status="completed",
    )[0]

    packet = SectionPacket(
        section_contract=contract,
        query="release readiness",
        project_context={"project_id": "demo"},
        evidence_pack=_build_evidence_pack(),
        research_summary="summary",
        relevant_state={"iteration": 1},
    )

    assert packet.section_contract.section_id == "risk_assessment"
    assert packet.project_context["project_id"] == "demo"
    assert packet.relevant_state["iteration"] == 1


def test_section_authoring_service_builds_section_artifacts_and_digests() -> None:
    contract_builder = SectionContractBuilder()
    authoring_service = SectionAuthoringService()
    contracts = contract_builder.build_release_readiness_contracts(
        evidence_pack=_build_evidence_pack(),
        review_status="completed",
    )

    artifacts = authoring_service.author_sections(
        contracts=contracts,
        query="release readiness",
        project_context={"project_id": "demo"},
        evidence_pack=_build_evidence_pack(),
        research_summary="summary",
        relevant_state={"review_status": "completed"},
    )

    assert len(artifacts) == 4
    assert artifacts[0].section_id == "risk_assessment"
    assert artifacts[0].digest.source_refs
    assert artifacts[0].metadata["project_context_keys"] == ["project_id"]


def test_section_authoring_workflow_builds_reviewed_section_artifact() -> None:
    contract = SectionContractBuilder().build_release_readiness_contracts(
        evidence_pack=_build_evidence_pack(),
        review_status="completed",
    )[0]
    workflow = SectionAuthoringWorkflow()

    result = workflow.invoke(
        SectionAuthoringState(
            task_context={"task_id": "task-1", "correlation_id": "corr-1", "section_id": contract.section_id},
            query="release readiness",
            section_contract=contract,
            project_context={"project_id": "demo"},
            evidence_pack=_build_evidence_pack(),
            research_summary="summary",
        )
    )

    assert result.final_section_artifact is not None
    assert result.final_section_artifact.section_id == "risk_assessment"
    assert result.final_section_artifact.review_status == "completed"
    assert result.review_result["recommendation"] == "conditional_go"
    assert result.final_section_artifact.metadata["section_review"]["section_id"] == "risk_assessment"


def test_section_authoring_workflow_resume_applies_human_feedback() -> None:
    contract = SectionContractBuilder().build_release_readiness_contracts(
        evidence_pack=_build_evidence_pack(),
        review_status="completed",
    )[1]
    workflow = SectionAuthoringWorkflow(use_langgraph_runtime=False)

    result = workflow.resume(
        SectionAuthoringState(
            query="release readiness",
            section_contract=contract,
            project_context={"project_id": "demo"},
            evidence_pack=_build_evidence_pack(),
            research_summary="summary",
            human_feedback={"comment": "Уточни approvals и ограничения."},
            iteration_count=1,
        )
    )

    assert result.iteration_count == 2
    assert result.final_section_artifact is not None
    assert "### Human Feedback" in result.final_section_artifact.content
    assert result.final_section_artifact.metadata["human_feedback_applied"] is True


def test_section_contract_builder_builds_contracts_from_custom_template() -> None:
    builder = SectionContractBuilder()

    template_spec, contracts = builder.build_contracts_from_template(
        template_id="decision_memo",
        evidence_pack=_build_evidence_pack(),
        review_status="completed",
        template_payload={
            "version": "2",
            "sections": [
                {
                    "section_id": "executive_summary",
                    "title": "Executive Summary",
                    "objective": "Summarize the key decision for executives.",
                    "required_keywords": ["approval", "decision"],
                    "source_hints": ["approval", "decision"],
                },
                {
                    "section_id": "risks",
                    "title": "Risks",
                    "objective": "List risks and constraints.",
                    "required_keywords": ["risk", "pending"],
                },
            ],
            "validation_rules": [{"rule_id": "non_empty", "description": "Sections must not be empty."}],
        },
    )

    assert template_spec.template_id == "decision_memo"
    assert template_spec.version == "2"
    assert len(template_spec.sections) == 2
    assert len(contracts) == 2
    assert contracts[0].section_id == "executive_summary"
    assert contracts[0].metadata["template_id"] == "decision_memo"
    assert contracts[1].preferred_source_refs


def test_template_compiler_and_catalog_support_assembly_rules() -> None:
    compiler = TemplateCompiler()
    template_spec = compiler.compile(
        template_id="board_memo",
        template_payload={
            "sections": [
                {"section_id": "decision", "title": "Decision"},
                {"section_id": "risks", "title": "Risks"},
            ],
            "assembly_rules": [
                {
                    "rule_id": "board_order",
                    "mode": "section_order",
                    "section_order": ["risks", "decision"],
                    "include_writer_draft": False,
                }
            ],
        },
    )

    assert template_spec.assembly_rules[0]["section_order"] == ["risks", "decision"]
    assert template_spec.assembly_rules[0]["include_writer_draft"] is False


def test_document_assembly_workflow_builds_final_document_and_export_payload() -> None:
    workflow = DocumentAssemblyWorkflow()
    template_spec = TemplateCompiler().compile(
        template_id="decision_memo",
        template_payload={
            "sections": [
                {"section_id": "executive_summary", "title": "Executive Summary"},
            ],
            "assembly_rules": [
                {
                    "rule_id": "decision_json",
                    "mode": "section_order",
                    "section_order": ["executive_summary"],
                    "include_writer_draft": False,
                    "include_traceability": True,
                }
            ],
        },
    )
    section_artifact = SectionAuthoringService().author_section(
        SectionPacket(
            section_contract=SectionContractBuilder().build_contracts_from_template(
                template_id="decision_memo",
                evidence_pack=_build_evidence_pack(),
                review_status="completed",
                template_payload={
                    "sections": [
                        {
                            "section_id": "executive_summary",
                            "title": "Executive Summary",
                            "objective": "Summarize decision.",
                        }
                    ]
                },
            )[1][0],
            query="prepare decision memo",
            project_context={"project_id": "demo"},
            evidence_pack=_build_evidence_pack(),
            research_summary="Research summary",
        )
    )

    result = workflow.invoke(
        {
            "task_context": {"task_id": "task-assembly-1", "correlation_id": "corr-assembly-1"},
            "query": "prepare decision memo",
            "artifact_type": "decision_memo",
            "artifact_title": "Decision Memo",
            "artifact_format": "json",
            "workflow_mode": "multi_step",
            "research_summary": "Research summary",
            "writer_draft": "Writer draft",
            "review_result": {"status": "completed", "recommendation": "go", "notes": "Ready.", "issues": []},
            "template_spec": template_spec.model_dump(mode="json"),
            "section_artifacts": [section_artifact],
            "section_traceability": [
                {
                    "section_id": "executive_summary",
                    "title": "Executive Summary",
                    "review_status": "completed",
                    "source_refs": [{"doc_id": "REQ-1", "version": "1", "block_id": "B-1"}],
                }
            ],
        }
    )

    assert result.assembled_content is not None
    assert "# Decision Memo" in result.assembled_content
    assert isinstance(result.export_result, dict)
    assert result.export_result["format"] == "json"
    assert result.final_document["format"] == "json"
    assert '"sections"' in result.final_document["content"]


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


def test_document_assembler_uses_template_spec_and_section_artifacts_when_present() -> None:
    assembler = DocumentAssembler()

    content = assembler.assemble_document(
        query="prepare decision memo",
        research_summary="Research summary",
        writer_draft="Writer draft",
        review_result={
            "status": "completed",
            "recommendation": "go",
            "notes": "Ready.",
            "issues": [],
        },
        section_traceability=[
            {
                "section_id": "executive_summary",
                "title": "Executive Summary",
                "review_status": "completed",
                "source_refs": [{"doc_id": "REQ-1", "version": "1", "block_id": "B-1"}],
            }
        ],
        workflow_mode="multi_step",
        template_spec=TemplateCompiler().compile(
            template_id="decision_memo",
            template_payload={
                "sections": [
                    {"section_id": "executive_summary", "title": "Executive Summary"},
                    {"section_id": "risk_log", "title": "Risk Log"},
                ]
            },
        ),
        section_artifacts=[
            SectionAuthoringService().author_section(
                SectionPacket(
                    section_contract=SectionContractBuilder().build_contracts_from_template(
                        template_id="decision_memo",
                        evidence_pack=_build_evidence_pack(),
                        review_status="completed",
                        template_payload={
                            "sections": [
                                {
                                    "section_id": "executive_summary",
                                    "title": "Executive Summary",
                                    "objective": "Summarize decision.",
                                }
                            ]
                        },
                    )[1][0],
                    query="prepare decision memo",
                    project_context={"project_id": "demo"},
                    evidence_pack=_build_evidence_pack(),
                    research_summary="Research summary",
                )
            )
        ],
    )

    assert "# Decision Memo" in content
    assert "## Executive Summary" in content
    assert "## Risk Log" in content
    assert "Section artifact is missing." in content


def test_document_assembler_respects_template_assembly_visibility_flags() -> None:
    assembler = DocumentAssembler()

    content = assembler.assemble_document(
        query="prepare board memo",
        research_summary="Research summary",
        writer_draft="Writer draft",
        review_result={
            "status": "completed",
            "recommendation": "go",
            "notes": "Ready.",
            "issues": [],
        },
        section_traceability=[
            {
                "section_id": "decision",
                "title": "Decision",
                "review_status": "completed",
                "source_refs": [{"doc_id": "REQ-1", "version": "1", "block_id": "B-1"}],
            }
        ],
        workflow_mode="multi_step",
        template_spec=TemplateCompiler().compile(
            template_id="board_memo",
            template_payload={
                "sections": [
                    {"section_id": "decision", "title": "Decision"},
                ],
                "assembly_rules": [
                    {
                        "rule_id": "board_compact",
                        "mode": "section_order",
                        "section_order": ["decision"],
                        "include_writer_draft": False,
                        "include_traceability": False,
                    }
                ],
            },
        ),
        section_artifacts=[
            SectionAuthoringService().author_section(
                SectionPacket(
                    section_contract=SectionContractBuilder().build_contracts_from_template(
                        template_id="board_memo",
                        evidence_pack=_build_evidence_pack(),
                        review_status="completed",
                        template_payload={
                            "sections": [
                                {
                                    "section_id": "decision",
                                    "title": "Decision",
                                    "objective": "Summarize decision.",
                                }
                            ]
                        },
                    )[1][0],
                    query="prepare board memo",
                    project_context={"project_id": "demo"},
                    evidence_pack=_build_evidence_pack(),
                    research_summary="Research summary",
                )
            )
        ],
    )

    assert "## Decision" in content
    assert "## Reviewer" in content
    assert "## Writer Draft" not in content
    assert "## Section Traceability" not in content


def test_artifact_exporter_renders_json_artifact() -> None:
    exporter = ArtifactExporter()
    section_artifact = SectionAuthoringService().author_section(
        SectionPacket(
            section_contract=SectionContractBuilder().build_contracts_from_template(
                template_id="board_memo",
                evidence_pack=_build_evidence_pack(),
                review_status="completed",
                template_payload={
                    "sections": [
                        {
                            "section_id": "decision",
                            "title": "Decision",
                            "objective": "Summarize decision.",
                        }
                    ],
                    "assembly_rules": [
                        {
                            "rule_id": "json_compact",
                            "mode": "section_order",
                            "section_order": ["decision"],
                            "include_writer_draft": False,
                            "include_traceability": False,
                        }
                    ],
                },
            )[1][0],
            query="prepare board memo",
            project_context={"project_id": "demo"},
            evidence_pack=_build_evidence_pack(),
            research_summary="Research summary",
        )
    )

    result = exporter.export(
        artifact_type="board_memo",
        artifact_title="Compact Board Memo",
        artifact_format="json",
        assembled_content="# Board Memo",
        query="prepare board memo",
        research_summary="Research summary",
        writer_draft="Writer draft",
        review_result={
            "status": "completed",
            "recommendation": "go",
            "notes": "Ready.",
            "issues": [],
        },
        template_spec=TemplateCompiler().compile(
            template_id="board_memo",
            template_payload={
                "sections": [{"section_id": "decision", "title": "Decision"}],
                "assembly_rules": [
                    {
                        "rule_id": "json_compact",
                        "mode": "section_order",
                        "section_order": ["decision"],
                        "include_writer_draft": False,
                        "include_traceability": False,
                    }
                ],
            },
        ),
        section_artifacts=[section_artifact],
        section_traceability=[
            {
                "section_id": "decision",
                "title": "Decision",
                "review_status": "completed",
                "source_refs": [{"doc_id": "REQ-1", "version": "1", "block_id": "B-1"}],
            }
        ],
    )

    assert result.format == "json"
    assert result.metadata["export_format_resolved"] == "json"
    assert '"sections"' in result.content
    assert '"writer_draft"' not in result.content
    assert '"traceability"' not in result.content


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


def test_writer_draft_service_applies_human_feedback_with_metadata() -> None:
    service = WriterDraftService()

    updated = service.apply_human_feedback(
        draft="## Writer Draft",
        comment="please add approvals",
        metadata={"reviewer": "qa", "priority": "high"},
    )

    assert "### Human Feedback" in updated
    assert "please add approvals" in updated
    assert "- reviewer: qa" in updated
    assert "- priority: high" in updated


def test_section_review_service_updates_non_informational_section_statuses() -> None:
    service = SectionReviewService()
    sections = [
        {"section_id": "risk_assessment", "review_status": "needs_revision"},
        {"section_id": "evidence_register", "review_status": "informational"},
    ]

    updated = service.set_section_review_status(sections=sections, review_status="approved")

    assert updated[0]["review_status"] == "approved"
    assert updated[1]["review_status"] == "informational"
