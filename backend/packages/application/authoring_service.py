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
    """Результат генерации authoring draft."""

    content: str
    mode: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class AuthoringApplicationService:
    """Application service authoring MVP: retrieval -> draft -> artifact."""

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

            artifact_title = request.artifact_title or "Release Readiness Draft"
            draft_result = self._generate_draft(
                query=request.query,
                evidence_pack=evidence_pack,
                draft_strategy=request.draft_strategy,
            )
            draft_content = draft_result.content

            artifact_metadata = {
                "authoring_task_id": task.task_id,
                "retrieval_task_id": retrieval_task_id,
                "source_count": len(evidence_pack.selected_sources),
                "draft_generation_mode": draft_result.mode,
                "draft_generation_requested_strategy": request.draft_strategy,
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
                    "content": draft_content,
                    "format": request.artifact_format,
                    "metadata": artifact_metadata,
                },
            )

            traceability = self._build_traceability(retrieval_task_id=retrieval_task_id, evidence_pack=evidence_pack)
            self._task_artifact_registry.save_link(
                task_id=task.task_id,
                artifact_id=artifact.artifact_id,
                retrieval_task_id=retrieval_task_id,
                traceability=traceability,
            )

            completed_state = initial_state.model_copy(
                update={
                    "retrieval_task_id": retrieval_task_id,
                    "artifact_id": artifact.artifact_id,
                    "draft": draft_content,
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
                    "traceability_sources": len(traceability.get("source_refs", [])),
                    "draft_generation_mode": draft_result.mode,
                },
            )
            return StartTaskResponse(task_id=task.task_id, status="completed")
        except Exception as exc:
            failed_state = initial_state.model_copy(update={"error_message": str(exc)})
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

        source_refs: list[SourceRef] = []
        for item in link.traceability.get("source_refs", []):
            source_refs.append(
                SourceRef(
                    doc_id=str(item.get("doc_id", "")),
                    version=str(item.get("version", "")),
                    block_id=str(item.get("block_id", "")),
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
            ),
        )

    def _generate_draft(
        self,
        *,
        query: str,
        evidence_pack: EvidencePack,
        draft_strategy: str,
    ) -> DraftGenerationResult:
        if draft_strategy not in {"auto", "deterministic", "llm"}:
            raise ValueError(f"Неподдерживаемый draft_strategy: {draft_strategy}")

        should_use_llm = draft_strategy == "llm" or (draft_strategy == "auto" and self._llm_enabled)
        if not should_use_llm:
            return DraftGenerationResult(
                content=self._build_draft_content(query=query, evidence_pack=evidence_pack),
                mode="deterministic",
            )

        if self._chat_model_gateway is None:
            reason = "LLM gateway не сконфигурирован для выбранной стратегии"
            if self._llm_strict_mode or draft_strategy == "llm":
                raise RuntimeError(reason)
            return DraftGenerationResult(
                content=self._build_draft_content(query=query, evidence_pack=evidence_pack),
                mode="deterministic_fallback",
                metadata={"fallback_reason": reason},
            )

        prompt = self._build_llm_prompt(query=query, evidence_pack=evidence_pack)
        try:
            generated = self._chat_model_gateway.generate(
                prompt,
                metadata={"temperature": 0.2, "max_tokens": 1000},
            )
        except Exception as exc:
            if self._llm_strict_mode or draft_strategy == "llm":
                raise
            return DraftGenerationResult(
                content=self._build_draft_content(query=query, evidence_pack=evidence_pack),
                mode="deterministic_fallback",
                metadata={"fallback_reason": str(exc)},
            )

        content = generated.strip()
        if not content:
            reason = "LLM вернула пустой draft"
            if self._llm_strict_mode or draft_strategy == "llm":
                raise RuntimeError(reason)
            return DraftGenerationResult(
                content=self._build_draft_content(query=query, evidence_pack=evidence_pack),
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

    def _build_draft_content(self, *, query: str, evidence_pack: EvidencePack) -> str:
        lines = [
            "# Authoring Draft",
            "",
            f"## Query",
            query.strip(),
            "",
            "## Evidence Highlights",
        ]

        for block in evidence_pack.selected_blocks[:5]:
            snippet = block.text.strip()
            if len(snippet) > 180:
                snippet = snippet[:177] + "..."
            lines.append(f"- {snippet} ({block.source.doc_id}/{block.source.block_id})")

        if not evidence_pack.selected_blocks:
            lines.append("- No evidence blocks returned by retrieval pipeline.")

        lines.extend(
            [
                "",
                "## Draft Decision",
                "Decision pending manual review.",
            ]
        )
        return "\n".join(lines)

    def _build_llm_prompt(self, *, query: str, evidence_pack: EvidencePack) -> str:
        """Собирает prompt для LLM-генерации release readiness draft."""

        lines = [
            "Подготовь краткий release readiness draft в markdown.",
            "",
            "Требования к структуре:",
            "1. Заголовок.",
            "2. Ключевые риски (bullet list).",
            "3. Pending approvals (bullet list).",
            "4. Рекомендация GO/NO-GO с обоснованием.",
            "5. Evidence sources (doc_id/version/block_id).",
            "",
            "Важно: не выдумывай факты, опирайся только на evidence.",
            "",
            "Запрос:",
            query.strip(),
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

    def _build_traceability(self, *, retrieval_task_id: str, evidence_pack: EvidencePack) -> dict[str, Any]:
        seen: set[tuple[str, str, str]] = set()
        source_refs: list[dict[str, str]] = []
        for source in evidence_pack.selected_sources:
            key = (source.doc_id, source.version, source.block_id)
            if key in seen:
                continue
            seen.add(key)
            source_refs.append(
                {
                    "doc_id": source.doc_id,
                    "version": source.version,
                    "block_id": source.block_id,
                }
            )

        return {
            "retrieval_task_id": retrieval_task_id,
            "source_refs": source_refs,
        }
