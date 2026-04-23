from __future__ import annotations

from application.canonical_document_service import CanonicalDocumentApplicationService, KnowledgeBlockRecord
from schemas.documents.contracts import CanonicalDocument
from schemas.rag.contracts import RetrievedBlock


def load_canonical_knowledge_dataset(
    canonical_document_service: CanonicalDocumentApplicationService,
    *,
    doc_ids: list[str] | None = None,
    limit: int = 1000,
) -> tuple[list[RetrievedBlock], list[RetrievedBlock]]:
    """Build retrieval summary/detail blocks from canonical Knowledge Factory output."""

    documents = canonical_document_service.list_documents(limit=limit).items
    if doc_ids:
        allowed_doc_ids = set(doc_ids)
        documents = [document for document in documents if document.doc_id in allowed_doc_ids]

    if not documents:
        raise ValueError("Canonical knowledge store не содержит документов для retrieval")

    summary_blocks: list[RetrievedBlock] = []
    detail_blocks: list[RetrievedBlock] = []
    document_by_id = {document.doc_id: document for document in documents}

    for document in documents:
        summary_blocks.extend(_document_to_summary_blocks(document))

    if doc_ids:
        for doc_id in doc_ids:
            detail_blocks.extend(
                _block_to_retrieved_block(block, document_by_id.get(block.doc_id))
                for block in canonical_document_service.list_blocks(limit=limit, doc_id=doc_id).items
                if block.doc_id in document_by_id
            )
    else:
        detail_blocks = [
            _block_to_retrieved_block(block, document_by_id.get(block.doc_id))
            for block in canonical_document_service.list_blocks(limit=limit).items
            if block.doc_id in document_by_id
        ]

    if not summary_blocks and not detail_blocks:
        raise ValueError("Canonical knowledge store не содержит retrieval blocks")
    return summary_blocks, detail_blocks


def _document_to_summary_blocks(document: CanonicalDocument) -> list[RetrievedBlock]:
    blocks: list[RetrievedBlock] = []
    base_metadata = _document_metadata(document)
    for summary in document.section_summaries:
        blocks.append(
            RetrievedBlock.model_validate(
                {
                    "text": summary.summary,
                    "source": {
                        "doc_id": document.doc_id,
                        "version": document.version,
                        "block_id": f"summary:{summary.section_id}",
                    },
                    "score": 0.0,
                    "metadata": {
                        **base_metadata,
                        **summary.metadata,
                        "block_kind": "section_summary",
                        "section_id": summary.section_id,
                        "section_title": summary.title,
                        "source_block_ids": summary.source_block_ids,
                    },
                }
            )
        )
    return blocks


def _block_to_retrieved_block(block: KnowledgeBlockRecord, document: CanonicalDocument | None) -> RetrievedBlock:
    metadata = _document_metadata(document) if document else {"project_id": "p1"}
    return RetrievedBlock.model_validate(
        {
            "text": block.text,
            "source": {
                "doc_id": block.doc_id,
                "version": block.version,
                "block_id": block.block_id,
            },
            "score": 0.0,
            "metadata": {
                **metadata,
                **block.metadata,
                "block_kind": "content_block",
                "block_type": block.block_type,
                "heading_path": block.heading_path,
            },
        }
    )


def _document_metadata(document: CanonicalDocument | None) -> dict:
    if document is None:
        return {"project_id": "p1"}

    profile = dict(document.metadata_profile)
    return {
        "project_id": profile.get("project_id", "p1"),
        "document_type": profile.get("document_type", "requirements"),
        "tags": profile.get("tags", []),
        "doc_title": profile.get("doc_title") or profile.get("file_name") or document.doc_id,
        "source_path": document.source_path,
        "file_type": document.file_type,
        "quality_flags": list(document.quality_flags),
    }
