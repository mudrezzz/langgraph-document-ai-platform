from __future__ import annotations

import argparse
import json
from pathlib import Path

from apps.api.dependencies import ApiContainer
from application.knowledge_indexing_service import KnowledgeIndexingApplicationService


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Smoke-проверка canonical document indexing")
    parser.add_argument(
        "--input-path",
        default="backend/examples/cases/release_go_no_go_multifile_case/input",
        help="Файл или директория документов для canonical indexing",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    container = ApiContainer()
    service = KnowledgeIndexingApplicationService(
        canonical_document_service=container.canonical_document_service,
        embedding_gateway=container.embedding_gateway,
        vector_store=container.vector_store,
    )
    result = service.index_paths(
        [Path(args.input_path)],
        task_context={"smoke": "knowledge_indexing"},
    )

    payload = {
        "documents_total": len(result.documents),
        "indexed_doc_ids": result.indexed_doc_ids,
        "quality_flags": result.quality_flags,
        "content_blocks_total": sum(len(document.content_blocks) for document in result.documents),
        "section_summaries_total": sum(len(document.section_summaries) for document in result.documents),
        "file_types": sorted({document.file_type for document in result.documents}),
        "stored_blocks_total": container.canonical_document_service.list_blocks(limit=200).total_returned,
        "embeddings_indexed": result.embeddings_indexed,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=4))


if __name__ == "__main__":
    main()
