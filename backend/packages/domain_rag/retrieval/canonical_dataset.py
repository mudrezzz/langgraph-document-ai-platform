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
    metadata_payload = {
        **metadata,
        **block.metadata,
        "block_kind": "content_block",
        "block_type": block.block_type,
        "heading_path": block.heading_path,
    }
    if block.block_type == "table_row":
        metadata_payload["source_kind"] = "table_row"
        metadata_payload["section_title"] = block.heading_path[-1] if block.heading_path else None
        metadata_payload["table_title"] = _resolve_table_title(document, block)
        metadata_payload["row_values"] = _resolve_table_row_values(document, block)

    return RetrievedBlock.model_validate(
        {
            "text": block.text,
            "source": {
                "doc_id": block.doc_id,
                "version": block.version,
                "block_id": block.block_id,
            },
            "score": 0.0,
            "metadata": metadata_payload,
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
        "parser_quality": document.parser_quality.model_dump(mode="json"),
    }


def _resolve_table_title(document: CanonicalDocument | None, block: KnowledgeBlockRecord) -> str | None:
    if document is None:
        return None
    table_id = str(block.metadata.get("table_id", "") or "").strip()
    if not table_id:
        return None
    table = next((item for item in document.extracted_tables if item.table_id == table_id), None)
    return table.title if table is not None else None


def _resolve_table_row_values(document: CanonicalDocument | None, block: KnowledgeBlockRecord) -> dict:
    if document is None:
        return {}
    table_id = str(block.metadata.get("table_id", "") or "").strip()
    row_index = block.metadata.get("row_index")
    if not table_id or not isinstance(row_index, int) or row_index < 1:
        return {}
    table = next((item for item in document.extracted_tables if item.table_id == table_id), None)
    if table is None or row_index > len(table.rows):
        return {}
    return dict(table.rows[row_index - 1])
