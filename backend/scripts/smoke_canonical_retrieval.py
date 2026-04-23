from __future__ import annotations

import argparse
import json
from pathlib import Path

from apps.api.dependencies import ApiContainer
from application.knowledge_indexing_service import KnowledgeIndexingApplicationService
from schemas.api.contracts import StartRetrievalTaskRequest
from schemas.rag.contracts import RetrievalFilter


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Smoke-проверка retrieval поверх canonical knowledge_blocks")
    parser.add_argument(
        "--input-path",
        default="backend/examples/cases/release_go_no_go_multifile_case/input",
        help="Файл или директория документов для canonical indexing перед retrieval",
    )
    parser.add_argument(
        "--query",
        default="что блокирует релиз и какие approvals pending",
        help="Retrieval query",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    container = ApiContainer()

    indexing_service = KnowledgeIndexingApplicationService(
        canonical_document_service=container.canonical_document_service,
    )
    indexing_result = indexing_service.index_paths(
        [Path(args.input_path)],
        task_context={"smoke": "canonical_retrieval"},
    )

    start_response = container.retrieval_service.start(
        StartRetrievalTaskRequest(
            query=args.query,
            filters=RetrievalFilter(
                project_id="p1",
                document_types=["requirements", "methodology", "security", "operations", "governance"],
            ),
            task_context={
                "requester": "canonical-retrieval-smoke",
                "knowledge_source": "canonical",
                "canonical_doc_ids": indexing_result.indexed_doc_ids,
            },
        )
    )
    status = container.retrieval_service.status(start_response.task_id)
    evidence = container.retrieval_service.evidence(start_response.task_id)

    payload = {
        "indexed_doc_ids": indexing_result.indexed_doc_ids,
        "stored_blocks_total": container.canonical_document_service.list_blocks(limit=500).total_returned,
        "task_id": start_response.task_id,
        "start_status": start_response.status,
        "task_status": status.status,
        "knowledge_source": status.details.get("knowledge_source"),
        "evidence_blocks": len(evidence.evidence_pack.selected_blocks),
        "top_sources": [source.model_dump(mode="json") for source in evidence.evidence_pack.selected_sources[:5]],
    }
    print(json.dumps(payload, ensure_ascii=False, indent=4))


if __name__ == "__main__":
    main()
