from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from domain_authoring.assembly import DocumentAssembler
from domain_authoring.contracts import SectionContractBuilder
from domain_authoring.exporter import ArtifactExporter
from domain_authoring.outline import OutlinePlanner
from domain_authoring.research import ResearchSummaryBuilder
from domain_authoring.review import SectionReviewService
from domain_authoring.workflows import DocumentAssemblyWorkflow, SectionAuthoringWorkflow
from domain_authoring.writer import WriterDraftService
from schemas.rag.contracts import EvidencePack
from schemas.workflow.states import AssemblyWorkflowState, SectionAuthoringState

from agent_examples.patterns.authoring_first.tools import (
    build_project_context,
    build_workflow_steps,
)
from agent_examples.patterns.retrieval_first.tools import build_default_filters
from agent_examples.patterns.retrieval_first.workflow import RetrievalWorkflowInput, run_retrieval_workflow


@dataclass(frozen=True)
class AuthoringWorkflowInput:
    query: str
    requester: str
    case_dataset_id: str
    template_id: str = "release_readiness"
    workflow_mode: str = "multi_step"
    draft_strategy: str = "deterministic"
    artifact_title: str = "Agent Examples: Policy Brief"
    artifact_format: str = "markdown"


def run_authoring_workflow(payload: AuthoringWorkflowInput) -> dict[str, Any]:
    retrieval_state = run_retrieval_workflow(
        RetrievalWorkflowInput(
            query=payload.query,
            filters=build_default_filters(),
            case_dataset_id=payload.case_dataset_id,
            requester=payload.requester,
        )
    )
    evidence_pack = _ensure_evidence_pack(retrieval_state.evidence_pack)

    project_context = build_project_context(
        requester=payload.requester,
        case_dataset_id=payload.case_dataset_id,
        workflow_mode=payload.workflow_mode,
        draft_strategy=payload.draft_strategy,
    )

    research_builder = ResearchSummaryBuilder()
    writer_service = WriterDraftService()
    review_service = SectionReviewService()
    contract_builder = SectionContractBuilder()
    outline_planner = OutlinePlanner()

    research_summary = research_builder.build_summary(query=payload.query, evidence_pack=evidence_pack)
    writer_draft = writer_service.build_deterministic_draft(
        query=payload.query,
        evidence_pack=evidence_pack,
        research_summary=research_summary,
    )
    review_result = review_service.review_draft(
        query=payload.query,
        draft=writer_draft,
        evidence_pack=evidence_pack,
        workflow_mode=payload.workflow_mode,
    )

    template_spec, section_contracts = contract_builder.build_contracts_from_template(
        template_id=payload.template_id,
        evidence_pack=evidence_pack,
        review_status=str(review_result.get("status", "not_reviewed")),
    )
    section_traceability = outline_planner.build_section_traceability(
        evidence_pack=evidence_pack,
        review_result=review_result,
        template_spec=template_spec,
        section_contracts=section_contracts,
    )

    section_workflow = SectionAuthoringWorkflow(use_langgraph_runtime=False)
    section_artifacts = []
    section_steps = []
    for contract in section_contracts:
        section_state = SectionAuthoringState(
            task_context={
                "requester": payload.requester,
                "case_dataset_id": payload.case_dataset_id,
                "section_id": contract.section_id,
            },
            query=payload.query,
            section_contract=contract,
            project_context=project_context,
            evidence_pack=evidence_pack,
            research_summary=research_summary,
            iteration_count=1,
        )
        section_result = section_workflow.invoke(section_state)
        if section_result.final_section_artifact is None:
            raise ValueError(f"Section artifact was not generated for section_id={contract.section_id}")
        section_artifacts.append(section_result.final_section_artifact)
        section_steps.append(
            {
                "name": f"section_authoring.{contract.section_id}",
                "status": "completed",
                "review_status": section_result.final_section_artifact.review_status,
                "source_refs_total": len(section_result.final_section_artifact.source_refs),
            }
        )

    assembly_workflow = DocumentAssemblyWorkflow(
        document_assembler=DocumentAssembler(),
        artifact_exporter=ArtifactExporter(),
        use_langgraph_runtime=False,
    )
    assembly_state = AssemblyWorkflowState(
        task_context={"requester": payload.requester, "case_dataset_id": payload.case_dataset_id},
        query=payload.query,
        artifact_type="release_report",
        artifact_title=payload.artifact_title,
        artifact_format=payload.artifact_format,
        workflow_mode=payload.workflow_mode,
        research_summary=research_summary,
        writer_draft=writer_draft,
        review_result=review_result,
        template_spec=template_spec.model_dump(mode="json"),
        section_artifacts=section_artifacts,
        section_traceability=section_traceability,
    )
    assembly_result = assembly_workflow.invoke(assembly_state)
    final_document = dict(assembly_result.final_document or {})
    export_result = dict(assembly_result.export_result or {})

    workflow_steps = build_workflow_steps(
        retrieval_confidence=retrieval_state.confidence,
        section_steps=section_steps,
        review_status=str(review_result.get("status", "unknown")),
        recommendation=str(review_result.get("recommendation", "pending_manual_review")),
    )
    traceability = outline_planner.build_traceability(
        retrieval_task_id="in_process_retrieval",
        evidence_pack=evidence_pack,
        section_traceability=section_traceability,
        workflow_steps=workflow_steps,
    )

    return {
        "query": payload.query,
        "workflow_mode": payload.workflow_mode,
        "draft_strategy": payload.draft_strategy,
        "artifact_title": payload.artifact_title,
        "artifact_format": payload.artifact_format,
        "retrieval_confidence": retrieval_state.confidence,
        "unresolved_gaps": retrieval_state.unresolved_gaps,
        "evidence_pack": evidence_pack,
        "research_summary": research_summary,
        "writer_draft": writer_draft,
        "review_result": review_result,
        "template_spec": template_spec.model_dump(mode="json"),
        "section_artifacts": [item.model_dump(mode="json") for item in section_artifacts],
        "section_traceability": section_traceability,
        "traceability": traceability,
        "workflow_steps": workflow_steps,
        "final_document": final_document,
        "export_result": export_result,
    }


def _ensure_evidence_pack(evidence_pack: EvidencePack | None) -> EvidencePack:
    if evidence_pack is None:
        return EvidencePack()
    return evidence_pack
