from __future__ import annotations

from datetime import datetime
from typing import Any, Protocol

from pydantic import BaseModel, Field

from application.artifact_service import ArtifactApplicationService
from application.errors import (
    InvalidTaskStateError,
    TaskArtifactLinkNotFoundError,
    WorkflowExecutionError,
)
from application.retrieval_service import RetrievalApplicationService
from application.task_service import TaskApplicationService
from framework.models.interfaces import IChatModelGateway
from schemas.api.contracts import (
    StartAuthoringTaskRequest,
    StartRetrievalTaskRequest,
    StartTaskResponse,
    TaskArtifactResponse,
    TaskArtifactSectionTraceabilityResponse,
    TaskArtifactTraceabilityResponse,
)
from schemas.rag.contracts import EvidencePack, SourceRef
from schemas.workflow.states import AuthoringTaskState


class TaskArtifactLinkRecord(BaseModel):
    """Связь authoring task с итоговым артефактом."""

    task_id: str
    artifact_id: str
    retrieval_task_id: str
    traceability: dict = Field(default_factory=dict)
    created_at: datetime | None = None
    updated_at: datetime | None = None


class TaskArtifactRegistry(Protocol):
    """Контракт хранения связи task -> artifact."""

    def save_link(
        self,
        *,
        task_id: str,
        artifact_id: str,
        retrieval_task_id: str,
        traceability: dict,
    ) -> None:
        """Сохраняет связь authoring task и артефакта."""

    def get_link(self, task_id: str) -> TaskArtifactLinkRecord:
        """Возвращает связь authoring task и артефакта."""


class DraftGenerationResult(BaseModel):
    """Результат writer-генерации authoring draft."""

    content: str
    mode: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class AuthoringStepResult(BaseModel):
    """Результат выполнения шага multi-step authoring."""

    step: str
    status: str
    notes: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class AuthoringApplicationService:
    """Application service authoring: retrieval -> research -> writer -> reviewer -> assembly."""

    def __init__(
        self,
        *,
        task_service: TaskApplicationService,
        retrieval_service: RetrievalApplicationService,
        artifact_service: ArtifactApplicationService,
        task_artifact_registry: TaskArtifactRegistry,
        chat_model_gateway: IChatModelGateway | None = None,
        llm_enabled: bool = False,
        llm_strict_mode: bool = False,
        llm_provider: str = "deterministic",
        llm_model_name: str | None = None,
    ) -> None:
        self._task_service = task_service
        self._retrieval_service = retrieval_service
        self._artifact_service = artifact_service
        self._task_artifact_registry = task_artifact_registry
        self._chat_model_gateway = chat_model_gateway
        self._llm_enabled = llm_enabled
        self._llm_strict_mode = llm_strict_mode
        self._llm_provider = llm_provider
        self._llm_model_name = llm_model_name

    def start(self, request: StartAuthoringTaskRequest) -> StartTaskResponse:
        task = self._task_service.create_task(task_type="authoring_pack")

        task_context = {**request.task_context, "task_id": task.task_id}
        initial_state = AuthoringTaskState(
            task_context=task_context,
            query=request.query,
            filters=request.filters,
            artifact_type=request.artifact_type,
            artifact_title=request.artifact_title,
            artifact_format=request.artifact_format,
            draft_strategy=request.draft_strategy,
            workflow_mode=request.workflow_mode,
            current_step="retrieval",
        )

        try:
            retrieval_request = StartRetrievalTaskRequest(
                query=request.query,
                filters=request.filters,
                task_context={
                    **task_context,
                    "parent_task_id": task.task_id,
                },
            )
            retrieval_started = self._retrieval_service.start(retrieval_request)
            retrieval_task_id = retrieval_started.task_id
            evidence_pack = self._retrieval_service.evidence(retrieval_task_id).evidence_pack

            steps: list[AuthoringStepResult] = []

            research_summary = self._build_research_summary(query=request.query, evidence_pack=evidence_pack)
            steps.append(
                AuthoringStepResult(
                    step="research",
                    status="completed",
                    notes="Собран исследовательский summary по evidence.",
                    metadata={"summary_length": len(research_summary)},
                )
            )

            draft_result = self._generate_draft(
                query=request.query,
                evidence_pack=evidence_pack,
                draft_strategy=request.draft_strategy,
                research_summary=research_summary,
            )
            steps.append(
                AuthoringStepResult(
                    step="writer",
                    status="completed",
                    notes="Сформирован writer draft.",
                    metadata={"generation_mode": draft_result.mode},
                )
            )

            review_result = self._review_draft(
                query=request.query,
                draft=draft_result.content,
                evidence_pack=evidence_pack,
                workflow_mode=request.workflow_mode,
            )
            steps.append(
                AuthoringStepResult(
                    step="reviewer",
                    status=review_result["status"],
                    notes=review_result["notes"],
                    metadata={
                        "recommendation": review_result["recommendation"],
                        "issues_count": len(review_result.get("issues", [])),
                    },
                )
            )

            section_traceability = self._build_section_traceability(evidence_pack=evidence_pack, review_result=review_result)
            final_content = self._assemble_document(
                query=request.query,
                research_summary=research_summary,
                writer_draft=draft_result.content,
                review_result=review_result,
                section_traceability=section_traceability,
                workflow_mode=request.workflow_mode,
            )
            steps.append(
                AuthoringStepResult(
                    step="assembly",
                    status="completed",
                    notes="Собран финальный артефакт.",
                    metadata={"section_count": len(section_traceability)},
                )
            )

            artifact_title = request.artifact_title or "Release Readiness Draft"
            artifact_metadata = {
                "authoring_task_id": task.task_id,
                "retrieval_task_id": retrieval_task_id,
                "source_count": len(evidence_pack.selected_sources),
                "draft_generation_mode": draft_result.mode,
                "draft_generation_requested_strategy": request.draft_strategy,
                "workflow_mode": request.workflow_mode,
                "review_status": review_result["status"],
                "final_recommendation": review_result["recommendation"],
                "steps_summary": [step.model_dump(mode="json") for step in steps],
            }
            if draft_result.metadata.get("provider"):
                artifact_metadata["draft_model_provider"] = draft_result.metadata["provider"]
            if draft_result.metadata.get("model_name"):
                artifact_metadata["draft_model_name"] = draft_result.metadata["model_name"]
            if draft_result.metadata.get("fallback_reason"):
                artifact_metadata["draft_fallback_reason"] = draft_result.metadata["fallback_reason"]

            artifact = self._artifact_service.write_artifact(
                artifact_type=request.artifact_type,
                payload={
                    "title": artifact_title,
                    "content": final_content,
                    "format": request.artifact_format,
                    "metadata": artifact_metadata,
                },
            )

            traceability = self._build_traceability(
                retrieval_task_id=retrieval_task_id,
                evidence_pack=evidence_pack,
                section_traceability=section_traceability,
                workflow_steps=steps,
            )
            self._task_artifact_registry.save_link(
                task_id=task.task_id,
                artifact_id=artifact.artifact_id,
                retrieval_task_id=retrieval_task_id,
                traceability=traceability,
            )

            completed_state = initial_state.model_copy(
                update={
                    "current_step": "completed",
                    "retrieval_task_id": retrieval_task_id,
                    "artifact_id": artifact.artifact_id,
                    "research_summary": research_summary,
                    "draft": draft_result.content,
                    "review_result": review_result,
                    "section_traceability": section_traceability,
                    "steps_summary": [step.model_dump(mode="json") for step in steps],
                    "traceability": traceability,
                    "draft_generation_mode": draft_result.mode,
                    "draft_generation_metadata": draft_result.metadata,
                }
            )
            self._task_service.complete_task(
                task_id=task.task_id,
                state_payload=completed_state.model_dump(mode="json"),
                details={
                    "artifact_id": artifact.artifact_id,
                    "artifact_type": artifact.artifact_type,
                    "retrieval_task_id": retrieval_task_id,
                    "current_step": "completed",
                    "workflow_mode": request.workflow_mode,
                    "traceability_sources": len(traceability.get("source_refs", [])),
                    "traceability_sections": len(traceability.get("sections", [])),
                    "draft_generation_mode": draft_result.mode,
                    "review_status": review_result["status"],
                    "final_recommendation": review_result["recommendation"],
                    "steps_summary": [step.model_dump(mode="json") for step in steps],
                },
            )
            return StartTaskResponse(task_id=task.task_id, status="completed")
        except Exception as exc:
            failed_state = initial_state.model_copy(update={"error_message": str(exc), "current_step": "failed"})
            self._task_service.fail_task(
                task_id=task.task_id,
                state_payload=failed_state.model_dump(mode="json"),
                error_message=str(exc),
            )
            raise WorkflowExecutionError(str(exc)) from exc

    def artifact(self, task_id: str) -> TaskArtifactResponse:
        task = self._task_service.get_task(task_id)
        if task.task_type != "authoring_pack":
            raise InvalidTaskStateError(
                f"Артефакт доступен только для задач authoring_pack, получен task_type={task.task_type}"
            )

        try:
            link = self._task_artifact_registry.get_link(task_id)
        except TaskArtifactLinkNotFoundError:
            raise

        artifact = self._artifact_service.get_artifact(link.artifact_id)
        payload = artifact.payload

        source_refs = self._to_source_refs(link.traceability.get("source_refs", []))
        sections_payload = link.traceability.get("sections", [])
        sections: list[TaskArtifactSectionTraceabilityResponse] = []
        for section in sections_payload:
            sections.append(
                TaskArtifactSectionTraceabilityResponse(
                    section_id=str(section.get("section_id", "")),
                    title=str(section.get("title", "")),
                    review_status=str(section.get("review_status", "not_reviewed")),
                    source_refs=self._to_source_refs(section.get("source_refs", [])),
                )
            )

        return TaskArtifactResponse(
            task_id=task_id,
            artifact_id=artifact.artifact_id,
            artifact_type=artifact.artifact_type,
            title=payload.get("title"),
            content=str(payload.get("content", "")),
            format=str(payload.get("format", "markdown")),
            metadata=dict(payload.get("metadata") or {}),
            traceability=TaskArtifactTraceabilityResponse(
                retrieval_task_id=link.retrieval_task_id,
                source_refs=source_refs,
                sections=sections,
            ),
        )

    def _to_source_refs(self, raw_refs: list[dict[str, Any]]) -> list[SourceRef]:
        refs: list[SourceRef] = []
        for item in raw_refs:
            refs.append(
                SourceRef(
                    doc_id=str(item.get("doc_id", "")),
                    version=str(item.get("version", "")),
                    block_id=str(item.get("block_id", "")),
                )
            )
        return refs

    def _build_research_summary(self, *, query: str, evidence_pack: EvidencePack) -> str:
        """Собирает research summary для следующего writer этапа."""

        lines = [
            "Запрос:",
            query.strip(),
            "",
            "Ключевые наблюдения:",
        ]

        for block in evidence_pack.selected_blocks[:6]:
            snippet = block.text.strip()
            if len(snippet) > 220:
                snippet = snippet[:217] + "..."
            lines.append(f"- {snippet} ({block.source.doc_id}/{block.source.block_id})")

        if not evidence_pack.selected_blocks:
            lines.append("- Retrieval не вернул блоки evidence.")

        return "\n".join(lines)

    def _generate_draft(
        self,
        *,
        query: str,
        evidence_pack: EvidencePack,
        draft_strategy: str,
        research_summary: str,
    ) -> DraftGenerationResult:
        if draft_strategy not in {"auto", "deterministic", "llm"}:
            raise ValueError(f"Неподдерживаемый draft_strategy: {draft_strategy}")

        should_use_llm = draft_strategy == "llm" or (draft_strategy == "auto" and self._llm_enabled)
        if not should_use_llm:
            return DraftGenerationResult(
                content=self._build_writer_draft_content(
                    query=query,
                    evidence_pack=evidence_pack,
                    research_summary=research_summary,
                ),
                mode="deterministic",
            )

        if self._chat_model_gateway is None:
            reason = "LLM gateway не сконфигурирован для выбранной стратегии"
            if self._llm_strict_mode or draft_strategy == "llm":
                raise RuntimeError(reason)
            return DraftGenerationResult(
                content=self._build_writer_draft_content(
                    query=query,
                    evidence_pack=evidence_pack,
                    research_summary=research_summary,
                ),
                mode="deterministic_fallback",
                metadata={"fallback_reason": reason},
            )

        prompt = self._build_llm_prompt(query=query, evidence_pack=evidence_pack, research_summary=research_summary)
        try:
            generated = self._chat_model_gateway.generate(
                prompt,
                metadata={"temperature": 0.2, "max_tokens": 1100},
            )
        except Exception as exc:
            if self._llm_strict_mode or draft_strategy == "llm":
                raise
            return DraftGenerationResult(
                content=self._build_writer_draft_content(
                    query=query,
                    evidence_pack=evidence_pack,
                    research_summary=research_summary,
                ),
                mode="deterministic_fallback",
                metadata={"fallback_reason": str(exc)},
            )

        content = generated.strip()
        if not content:
            reason = "LLM вернула пустой writer draft"
            if self._llm_strict_mode or draft_strategy == "llm":
                raise RuntimeError(reason)
            return DraftGenerationResult(
                content=self._build_writer_draft_content(
                    query=query,
                    evidence_pack=evidence_pack,
                    research_summary=research_summary,
                ),
                mode="deterministic_fallback",
                metadata={"fallback_reason": reason},
            )

        return DraftGenerationResult(
            content=content,
            mode="llm",
            metadata={
                "provider": self._llm_provider,
                "model_name": self._llm_model_name,
            },
        )

    def _build_writer_draft_content(self, *, query: str, evidence_pack: EvidencePack, research_summary: str) -> str:
        """Собирает writer draft без внешней LLM."""

        lines = [
            "## Writer Draft",
            "",
            "### Intent",
            query.strip(),
            "",
            "### Research Digest",
            research_summary,
            "",
            "### Risk Signals",
        ]

        risk_keywords = ("risk", "block", "pending", "fail", "critical", "approval")
        risk_blocks: list[str] = []
        for block in evidence_pack.selected_blocks[:10]:
            lowered = block.text.lower()
            if any(keyword in lowered for keyword in risk_keywords):
                snippet = block.text.strip()
                if len(snippet) > 180:
                    snippet = snippet[:177] + "..."
                risk_blocks.append(f"- {snippet} ({block.source.doc_id}/{block.source.block_id})")

        if risk_blocks:
            lines.extend(risk_blocks[:5])
        else:
            lines.append("- Явные risk-signal блоки не найдены, нужна ручная проверка.")

        lines.extend(
            [
                "",
                "### Preliminary Recommendation",
                "Decision pending reviewer validation.",
            ]
        )
        return "\n".join(lines)

    def _review_draft(
        self,
        *,
        query: str,
        draft: str,
        evidence_pack: EvidencePack,
        workflow_mode: str,
    ) -> dict[str, Any]:
        """Выполняет reviewer этап и выдает итоговую рекомендацию."""

        _ = query, draft
        if workflow_mode == "single_pass":
            return {
                "status": "skipped",
                "notes": "Reviewer этап пропущен в single_pass режиме.",
                "recommendation": "pending_manual_review",
                "issues": [],
            }

        risk_keywords = ("pending", "block", "critical", "fail", "no-go", "risk")
        approval_keywords = ("approval", "approve", "governance", "security")

        risk_count = 0
        approval_mentions = 0
        issues: list[str] = []

        for block in evidence_pack.selected_blocks:
            lowered = block.text.lower()
            if any(word in lowered for word in risk_keywords):
                risk_count += 1
            if any(word in lowered for word in approval_keywords):
                approval_mentions += 1

        if not evidence_pack.selected_blocks:
            issues.append("Нет evidence блоков для reviewer проверки.")
        if risk_count == 0:
            issues.append("Risk-сигналы в evidence почти не выражены.")
        if approval_mentions == 0:
            issues.append("Не обнаружены явные approval-ссылки.")

        if not evidence_pack.selected_blocks:
            recommendation = "no_go"
            status = "needs_revision"
            notes = "Недостаточно evidence для релизного решения."
        elif risk_count >= 2:
            recommendation = "no_go"
            status = "needs_revision"
            notes = "Обнаружены выраженные risk-сигналы и pending ограничения."
        elif approval_mentions >= 1:
            recommendation = "conditional_go"
            status = "completed"
            notes = "Есть approval-контекст, но требуется контроль оставшихся ограничений."
        else:
            recommendation = "go"
            status = "completed"
            notes = "Критичные риск-сигналы не выявлены, evidence достаточно для GO." 

        return {
            "status": status,
            "notes": notes,
            "recommendation": recommendation,
            "issues": issues,
            "risk_count": risk_count,
            "approval_mentions": approval_mentions,
        }

    def _build_section_traceability(self, *, evidence_pack: EvidencePack, review_result: dict[str, Any]) -> list[dict[str, Any]]:
        """Формирует traceability на уровне секций итогового документа."""

        unique_sources = self._dedup_source_dicts(evidence_pack.selected_sources)
        risk_sources = self._select_sources_by_keywords(
            evidence_pack=evidence_pack,
            keywords=("risk", "block", "critical", "pending", "no-go"),
            limit=3,
        )
        approval_sources = self._select_sources_by_keywords(
            evidence_pack=evidence_pack,
            keywords=("approval", "governance", "security", "policy", "pending"),
            limit=3,
        )

        return [
            {
                "section_id": "risk_assessment",
                "title": "Risk Assessment",
                "review_status": review_result.get("status", "not_reviewed"),
                "source_refs": risk_sources or unique_sources[:2],
            },
            {
                "section_id": "pending_approvals",
                "title": "Pending Approvals",
                "review_status": review_result.get("status", "not_reviewed"),
                "source_refs": approval_sources or unique_sources[:2],
            },
            {
                "section_id": "final_recommendation",
                "title": "Final Recommendation",
                "review_status": review_result.get("status", "not_reviewed"),
                "source_refs": unique_sources[:3],
            },
            {
                "section_id": "evidence_register",
                "title": "Evidence Register",
                "review_status": "informational",
                "source_refs": unique_sources,
            },
        ]

    def _assemble_document(
        self,
        *,
        query: str,
        research_summary: str,
        writer_draft: str,
        review_result: dict[str, Any],
        section_traceability: list[dict[str, Any]],
        workflow_mode: str,
    ) -> str:
        """Собирает финальный документ из результатов шагов authoring."""

        if workflow_mode == "single_pass":
            return writer_draft

        lines = [
            "# Release Readiness Report",
            "",
            "## Query",
            query.strip(),
            "",
            "## Research",
            research_summary,
            "",
            "## Writer",
            writer_draft,
            "",
            "## Reviewer",
            f"- status: {review_result.get('status', 'unknown')}",
            f"- recommendation: {review_result.get('recommendation', 'pending_manual_review')}",
            f"- notes: {review_result.get('notes', '-')}",
        ]

        issues = review_result.get("issues", []) or []
        lines.append("- issues:")
        if issues:
            for issue in issues:
                lines.append(f"  - {issue}")
        else:
            lines.append("  - none")

        lines.extend(["", "## Section Traceability"]) 
        for section in section_traceability:
            lines.append(
                f"- {section['section_id']} ({section['title']}), review_status={section.get('review_status', 'not_reviewed')}"
            )
            for source in section.get("source_refs", [])[:5]:
                lines.append(f"  - {source['doc_id']}/{source['version']}/{source['block_id']}")

        return "\n".join(lines)

    def _build_llm_prompt(self, *, query: str, evidence_pack: EvidencePack, research_summary: str) -> str:
        """Собирает prompt для LLM writer этапа."""

        lines = [
            "Подготовь writer-черновик release readiness в markdown.",
            "",
            "Структура:",
            "1. Risk Assessment.",
            "2. Pending Approvals.",
            "3. Preliminary Recommendation.",
            "4. Evidence Sources.",
            "",
            "Важно: используй только evidence и research summary, не выдумывай факты.",
            "",
            "Запрос:",
            query.strip(),
            "",
            "Research summary:",
            research_summary,
            "",
            "Evidence blocks:",
        ]

        for block in evidence_pack.selected_blocks[:10]:
            snippet = block.text.strip()
            if len(snippet) > 500:
                snippet = snippet[:497] + "..."
            lines.append(f"- [{block.source.doc_id}/{block.source.version}/{block.source.block_id}] {snippet}")

        if not evidence_pack.selected_blocks:
            lines.append("- evidence blocks отсутствуют")

        lines.extend(
            [
                "",
                "Evidence sources:",
            ]
        )
        for source in evidence_pack.selected_sources[:20]:
            lines.append(f"- {source.doc_id}/{source.version}/{source.block_id}")

        return "\n".join(lines)

    def _select_sources_by_keywords(
        self,
        *,
        evidence_pack: EvidencePack,
        keywords: tuple[str, ...],
        limit: int,
    ) -> list[dict[str, str]]:
        selected: list[dict[str, str]] = []
        seen: set[tuple[str, str, str]] = set()
        for block in evidence_pack.selected_blocks:
            lowered = block.text.lower()
            if not any(keyword in lowered for keyword in keywords):
                continue
            key = (block.source.doc_id, block.source.version, block.source.block_id)
            if key in seen:
                continue
            seen.add(key)
            selected.append(
                {
                    "doc_id": block.source.doc_id,
                    "version": block.source.version,
                    "block_id": block.source.block_id,
                }
            )
            if len(selected) >= limit:
                break
        return selected

    def _dedup_source_dicts(self, sources: list[SourceRef]) -> list[dict[str, str]]:
        deduped: list[dict[str, str]] = []
        seen: set[tuple[str, str, str]] = set()
        for source in sources:
            key = (source.doc_id, source.version, source.block_id)
            if key in seen:
                continue
            seen.add(key)
            deduped.append(
                {
                    "doc_id": source.doc_id,
                    "version": source.version,
                    "block_id": source.block_id,
                }
            )
        return deduped

    def _build_traceability(
        self,
        *,
        retrieval_task_id: str,
        evidence_pack: EvidencePack,
        section_traceability: list[dict[str, Any]],
        workflow_steps: list[AuthoringStepResult],
    ) -> dict[str, Any]:
        source_refs = self._dedup_source_dicts(evidence_pack.selected_sources)

        return {
            "retrieval_task_id": retrieval_task_id,
            "source_refs": source_refs,
            "sections": section_traceability,
            "workflow_steps": [step.model_dump(mode="json") for step in workflow_steps],
        }
