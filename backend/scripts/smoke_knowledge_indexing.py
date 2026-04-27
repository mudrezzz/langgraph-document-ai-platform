from __future__ import annotations

import argparse
import json
from pathlib import Path

from apps.api.dependencies import ApiContainer
from scripts.build_binary_demo_documents import build_binary_demo_documents


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Smoke-проверка canonical document indexing")
    parser.add_argument(
        "--input-path",
        default="backend/examples/cases/release_go_no_go_multifile_case/input",
        help="Файл или директория документов для canonical indexing",
    )
    parser.add_argument(
        "--build-binary-demo-docs",
        action="store_true",
        help="Перед smoke сгенерировать DOCX/PDF demo input files",
    )
    parser.add_argument(
        "--document-version",
        default="1",
        help="Версия canonical documents для текущего indexing run",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.build_binary_demo_docs:
        _build_binary_demo_docs(Path(args.input_path))

    container = ApiContainer()
    result = container.knowledge_indexing_service.index_paths(
        [Path(args.input_path)],
        task_context={"smoke": "knowledge_indexing"},
        document_version=args.document_version,
    )

    payload = {
        "documents_total": len(result.documents),
        "indexed_doc_ids": result.indexed_doc_ids,
        "document_version": args.document_version,
        "quality_flags": result.quality_flags,
        "parser_quality": {
            document.doc_id: document.parser_quality.model_dump(mode="json") for document in result.documents
        },
        "parser_quality_summary": result.quality_summary,
        "ocr_recovered_doc_ids": [
            document.doc_id for document in result.documents if "ocr_applied" in document.parser_quality.flags
        ],
        "content_blocks_total": sum(len(document.content_blocks) for document in result.documents),
        "section_summaries_total": sum(len(document.section_summaries) for document in result.documents),
        "file_types": sorted({document.file_type for document in result.documents}),
        "stored_blocks_total": container.canonical_document_service.list_blocks(limit=200).total_returned,
        "stored_blocks_for_indexed_docs_total": sum(
            container.canonical_document_service.list_blocks(limit=500, doc_id=doc_id).total_returned
            for doc_id in result.indexed_doc_ids
        ),
        "embeddings_indexed": result.embeddings_indexed,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=4))


def _build_binary_demo_docs(input_path: Path) -> None:
    if input_path.is_file():
        input_dir = input_path.parent
    else:
        input_dir = input_path
    build_binary_demo_documents(output_dir=input_dir)


if __name__ == "__main__":
    main()
