from __future__ import annotations

from application.document_service import DocumentApplicationService
from domain_docs.indexing.workflows import KnowledgeIndexingWorkflow
from schemas.documents.contracts import CanonicalDocument


class DocumentApplicationCanonicalStore:
    """Adapter from canonical indexing workflow to document application service."""

    def __init__(self, document_service: DocumentApplicationService) -> None:
        self._document_service = document_service

    def save_document(self, document: CanonicalDocument) -> str:
        record = self._document_service.upsert_document(
            doc_id=document.doc_id,
            payload=document.model_dump(mode="json"),
        )
        return record.doc_id


def build_knowledge_indexing_workflow(
    *,
    document_service: DocumentApplicationService,
    checkpointer: object | None = None,
) -> KnowledgeIndexingWorkflow:
    return KnowledgeIndexingWorkflow(
        store=DocumentApplicationCanonicalStore(document_service),
        checkpointer=checkpointer,
    )
