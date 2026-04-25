from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from domain_authoring.assembly import DocumentAssembler
from domain_authoring.exporter import ArtifactExportResult, ArtifactExporter
from domain_authoring.review import SectionReviewService
from domain_authoring.section_authoring import SectionAuthoringService
from framework.workflows import BaseWorkflow, WorkflowExecutionContext, WorkflowNodeSpec
from schemas.authoring.contracts import SectionArtifact, SectionPacket
from schemas.documents.contracts import TemplateSpec
from schemas.workflow.states import AssemblyWorkflowState, SectionAuthoringState


class SectionAuthoringWorkflow(BaseWorkflow):
    """Baseline section workflow over existing deterministic section services."""

    def __init__(
        self,
        *,
        section_authoring_service: SectionAuthoringService | None = None,
        section_review_service: SectionReviewService | None = None,
        use_langgraph_runtime: bool = True,
        checkpointer: object | None = None,
        node_event_sink=None,
    ) -> None:
        super().__init__(
            use_langgraph_runtime=use_langgraph_runtime,
            checkpointer=checkpointer,
            node_event_sink=node_event_sink,
        )
        self._section_authoring_service = section_authoring_service or SectionAuthoringService()
        self._section_review_service = section_review_service or SectionReviewService()
        self.compile()

    def state_schema(self) -> type[SectionAuthoringState]:
        return SectionAuthoringState

    def workflow_nodes(self, *, is_resume: bool):
        if is_resume:
            return [
                WorkflowNodeSpec(name="rewrite_section", handler=self._rewrite_section),
                WorkflowNodeSpec(name="review_section", handler=self._review_section),
                WorkflowNodeSpec(name="finalize_section", handler=self._finalize_section),
            ]
        return [
            WorkflowNodeSpec(name="write_section", handler=self._write_section),
            WorkflowNodeSpec(name="review_section", handler=self._review_section),
            WorkflowNodeSpec(name="finalize_section", handler=self._finalize_section),
        ]

    def _write_section(self, state: BaseModel, context: WorkflowExecutionContext) -> BaseModel:
        validated = SectionAuthoringState.model_validate(state)
        artifact = self._section_authoring_service.author_section(self._build_packet(validated))
        metadata = dict(artifact.metadata)
        metadata.update(
            {
                "workflow_node": context.node_name,
                "workflow_iteration": max(1, validated.iteration_count or 0),
            }
        )
        return validated.model_copy(
            update={
                "draft": artifact.content,
                "iteration_count": max(1, validated.iteration_count or 0),
                "final_section_artifact": artifact.model_copy(update={"metadata": metadata}),
            }
        )

    def _rewrite_section(self, state: BaseModel, context: WorkflowExecutionContext) -> BaseModel:
        validated = SectionAuthoringState.model_validate(state)
        rewritten = SectionAuthoringState.model_validate(self._write_section(validated, context))
        feedback_comment = self._feedback_comment(validated)
        if not feedback_comment:
            return rewritten.model_copy(update={"iteration_count": max(1, validated.iteration_count) + 1})

        artifact = self._require_artifact(rewritten)
        content = artifact.content + f"\n\n### Human Feedback\n{feedback_comment}"
        metadata = dict(artifact.metadata)
        metadata["human_feedback_applied"] = True
        metadata["workflow_iteration"] = max(1, validated.iteration_count) + 1
        return rewritten.model_copy(
            update={
                "draft": content,
                "iteration_count": max(1, validated.iteration_count) + 1,
                "final_section_artifact": artifact.model_copy(update={"content": content, "metadata": metadata}),
            }
        )

    def _review_section(self, state: BaseModel, context: WorkflowExecutionContext) -> BaseModel:
        validated = SectionAuthoringState.model_validate(state)
        artifact = self._require_artifact(validated)
        if validated.evidence_pack is None:
            raise ValueError("SectionAuthoringWorkflow требует evidence_pack для section review")

        review_result = self._section_review_service.review_draft(
            query=validated.query,
            draft=artifact.content,
            evidence_pack=validated.evidence_pack,
            workflow_mode="multi_step",
        )
        review_result["section_id"] = artifact.section_id
        review_result["review_node"] = context.node_name
        return validated.model_copy(update={"draft": artifact.content, "review_result": review_result})

    def _finalize_section(self, state: BaseModel, context: WorkflowExecutionContext) -> BaseModel:
        validated = SectionAuthoringState.model_validate(state)
        artifact = self._require_artifact(validated)
        review_result = dict(validated.review_result or {})
        review_status = artifact.review_status
        if review_status != "informational" and review_result.get("status"):
            review_status = str(review_result.get("status"))
        metadata = dict(artifact.metadata)
        metadata.update(
            {
                "section_review": review_result,
                "workflow_node": context.node_name,
                "workflow_iteration": max(1, validated.iteration_count or 0),
            }
        )
        return validated.model_copy(
            update={
                "final_section_artifact": artifact.model_copy(update={"review_status": review_status, "metadata": metadata}),
            }
        )

    def _build_packet(self, state: SectionAuthoringState) -> SectionPacket:
        if state.section_contract is None:
            raise ValueError("SectionAuthoringWorkflow требует section_contract")
        if state.evidence_pack is None:
            raise ValueError("SectionAuthoringWorkflow требует evidence_pack")
        return SectionPacket(
            section_contract=state.section_contract,
            query=state.query,
            project_context=state.project_context,
            evidence_pack=state.evidence_pack,
            research_summary=state.research_summary,
            relevant_state={"iteration": state.iteration_count, **(state.human_feedback or {})},
        )

    def _feedback_comment(self, state: SectionAuthoringState) -> str:
        if not isinstance(state.human_feedback, dict):
            return ""
        return str(state.human_feedback.get("comment", "")).strip()

    def _require_artifact(self, state: SectionAuthoringState) -> SectionArtifact:
        if state.final_section_artifact is None:
            raise ValueError("SectionAuthoringWorkflow не сформировал final_section_artifact")
        return state.final_section_artifact


class DocumentAssemblyWorkflow(BaseWorkflow):
    """Baseline workflow for final deterministic document assembly and export."""

    def __init__(
        self,
        *,
        document_assembler: DocumentAssembler | None = None,
        artifact_exporter: ArtifactExporter | None = None,
        use_langgraph_runtime: bool = True,
        checkpointer: object | None = None,
        node_event_sink=None,
    ) -> None:
        super().__init__(
            use_langgraph_runtime=use_langgraph_runtime,
            checkpointer=checkpointer,
            node_event_sink=node_event_sink,
        )
        self._document_assembler = document_assembler or DocumentAssembler()
        self._artifact_exporter = artifact_exporter or ArtifactExporter()
        self.compile()

    def state_schema(self) -> type[AssemblyWorkflowState]:
        return AssemblyWorkflowState

    def workflow_nodes(self, *, is_resume: bool):
        first_node = "reassemble_document" if is_resume else "assemble_document"
        first_handler = self._assemble_document if not is_resume else self._reassemble_document
        return [
            WorkflowNodeSpec(name=first_node, handler=first_handler),
            WorkflowNodeSpec(name="export_artifact", handler=self._export_artifact),
            WorkflowNodeSpec(name="finalize_document", handler=self._finalize_document),
        ]

    def _assemble_document(self, state: BaseModel, context: WorkflowExecutionContext) -> BaseModel:
        validated = AssemblyWorkflowState.model_validate(state)
        template_spec = self._template_spec(validated)
        assembled_content = self._document_assembler.assemble_document(
            query=validated.query,
            research_summary=validated.research_summary or "",
            writer_draft=validated.writer_draft or "",
            review_result=dict(validated.review_result),
            section_traceability=list(validated.section_traceability),
            workflow_mode=validated.workflow_mode,
            template_spec=template_spec,
            section_artifacts=list(validated.section_artifacts),
        )
        return validated.model_copy(
            update={
                "assembled_content": assembled_content,
                "final_document": {
                    "assembled_content": assembled_content,
                    "assembly_node": context.node_name,
                },
            }
        )

    def _reassemble_document(self, state: BaseModel, context: WorkflowExecutionContext) -> BaseModel:
        return self._assemble_document(state, context)

    def _export_artifact(self, state: BaseModel, context: WorkflowExecutionContext) -> BaseModel:
        validated = AssemblyWorkflowState.model_validate(state)
        template_spec = self._template_spec(validated)
        export_result = self._artifact_exporter.export(
            artifact_type=validated.artifact_type,
            artifact_title=validated.artifact_title,
            artifact_format=validated.artifact_format,
            assembled_content=validated.assembled_content or "",
            query=validated.query,
            research_summary=validated.research_summary or "",
            writer_draft=validated.writer_draft or "",
            review_result=dict(validated.review_result),
            template_spec=template_spec,
            section_artifacts=list(validated.section_artifacts),
            section_traceability=list(validated.section_traceability),
        )
        export_payload = export_result.model_dump(mode="json")
        export_payload["metadata"] = {
            **dict(export_result.metadata),
            "workflow_node": context.node_name,
        }
        return validated.model_copy(update={"export_result": export_payload})

    def _finalize_document(self, state: BaseModel, context: WorkflowExecutionContext) -> BaseModel:
        validated = AssemblyWorkflowState.model_validate(state)
        export_result = ArtifactExportResult.model_validate(validated.export_result or {})
        final_document = {
            "content": export_result.content,
            "format": export_result.format,
            "metadata": {
                **dict(export_result.metadata),
                "workflow_node": context.node_name,
                "assembled_content": validated.assembled_content or "",
            },
        }
        return validated.model_copy(update={"final_document": final_document})

    def _template_spec(self, state: AssemblyWorkflowState) -> TemplateSpec:
        payload = state.template_spec if isinstance(state.template_spec, dict) and state.template_spec else {
            "template_id": "release_readiness",
            "version": "1",
            "sections": [],
            "validation_rules": [],
            "assembly_rules": [],
        }
        return TemplateSpec.model_validate(payload)
