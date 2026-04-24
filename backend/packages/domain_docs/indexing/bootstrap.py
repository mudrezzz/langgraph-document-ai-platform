from __future__ import annotations

from application.canonical_document_service import CanonicalDocumentApplicationService
from domain_docs.indexing.workflows import KnowledgeIndexingWorkflow
from framework.workflows.base import WorkflowNodeEventSink
from schemas.documents.contracts import CanonicalDocument


class DocumentApplicationCanonicalStore:
    """Adapter from canonical indexing workflow to document application service."""

    def __init__(self, canonical_document_service: CanonicalDocumentApplicationService) -> None:
        self._canonical_document_service = canonical_document_service

    def save_document(self, document: CanonicalDocument) -> str:
        return self._canonical_document_service.save_document(document)


def build_knowledge_indexing_workflow(
    *,
    canonical_document_service: CanonicalDocumentApplicationService,
    checkpointer: object | None = None,
    node_event_sink: WorkflowNodeEventSink | None = None,
) -> KnowledgeIndexingWorkflow:
    return KnowledgeIndexingWorkflow(
        store=DocumentApplicationCanonicalStore(canonical_document_service),
        checkpointer=checkpointer,
        node_event_sink=node_event_sink,
    )
