from __future__ import annotations

from typing import Protocol

from framework.workflows.base import BaseWorkflow, WorkflowNodeEventSink
from schemas.documents.contracts import CanonicalDocument
from schemas.workflow.states import KnowledgeIndexingState


class CanonicalDocumentStore(Protocol):
    """Minimal storage port for canonical documents."""

    def save_document(self, document: CanonicalDocument) -> str:
        """Persist one canonical document and return its doc_id."""


class KnowledgeIndexingWorkflow(BaseWorkflow):
    """LangGraph-backed canonical indexing workflow MVP."""

    def __init__(
        self,
        store: CanonicalDocumentStore,
        checkpointer: object | None = None,
        node_event_sink: WorkflowNodeEventSink | None = None,
    ) -> None:
        super().__init__(use_langgraph_runtime=True, checkpointer=checkpointer, node_event_sink=node_event_sink)
        self._store = store
        self.compile()

    def state_schema(self) -> type[KnowledgeIndexingState]:
        return KnowledgeIndexingState

    def execute(self, state: KnowledgeIndexingState) -> KnowledgeIndexingState:
        if not state.documents:
            raise ValueError("KnowledgeIndexingWorkflow требует хотя бы один canonical document")

        indexed_doc_ids: list[str] = []
        quality_flags: list[str] = []
        for document in state.documents:
            indexed_doc_ids.append(self._store.save_document(document))
            quality_flags.extend(f"{document.doc_id}:{flag}" for flag in document.quality_flags)

        return state.model_copy(
            update={
                "indexed_doc_ids": indexed_doc_ids,
                "quality_flags": quality_flags,
            }
        )

    def execute_resume(self, state: KnowledgeIndexingState) -> KnowledgeIndexingState:
        return self.execute(state)
