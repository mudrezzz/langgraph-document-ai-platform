from __future__ import annotations

import argparse
import json
from pathlib import Path

from apps.api.dependencies import ApiContainer
from infra.fastmcp.retrieval_service import FastMcpRetrievalService
from scripts.build_binary_demo_documents import build_binary_demo_documents


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Smoke-проверка Retrieval MCP indexed canonical tools")
    parser.add_argument(
        "--input-path",
        default="backend/examples/cases/release_go_no_go_multifile_case/input",
        help="Файл или директория документов для canonical indexing перед MCP smoke",
    )
    parser.add_argument(
        "--query",
        default="security approval pending",
        help="Поисковый запрос для indexed summary/detail tools",
    )
    parser.add_argument("--project-id", default="p1", help="Project id для MCP search/build_evidence_pack")
    parser.add_argument(
        "--document-types",
        default="requirements,methodology,security,operations,governance",
        help="Список document types через запятую",
    )
    parser.add_argument(
        "--tags",
        default="",
        help="Опциональный список tags через запятую для MCP search tools",
    )
    parser.add_argument("--summary-limit", type=int, default=5, help="Лимит для search_summaries")
    parser.add_argument("--block-limit", type=int, default=5, help="Лимит для search_blocks")
    parser.add_argument(
        "--build-binary-demo-docs",
        action="store_true",
        help="Перед smoke сгенерировать DOCX/PDF demo input files",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    input_path = Path(args.input_path)
    if args.build_binary_demo_docs:
        _build_binary_demo_docs(input_path)

    container = ApiContainer()
    service = FastMcpRetrievalService(
        container.retrieval_service,
        canonical_document_service=container.canonical_document_service,
        embedding_gateway=container.embedding_gateway,
        vector_store=container.vector_store,
    )
    service.register_tools()

    indexing_result = container.knowledge_indexing_service.index_paths(
        [input_path],
        task_context={"smoke": "retrieval_mcp"},
    )
    document_types = _parse_csv(args.document_types)
    tags = _parse_csv(args.tags)
    indexed_doc_ids = indexing_result.indexed_doc_ids

    summaries = service.search_summaries(
        {
            "query": args.query,
            "project_id": args.project_id,
            "document_types": document_types,
            "tags": tags,
            "canonical_doc_ids": indexed_doc_ids,
            "limit": args.summary_limit,
        }
    )
    blocks = service.search_blocks(
        {
            "query": args.query,
            "project_id": args.project_id,
            "document_types": document_types,
            "tags": tags,
            "canonical_doc_ids": indexed_doc_ids,
            "limit": args.block_limit,
        }
    )

    if summaries["total_returned"] < 1:
        raise RuntimeError("search_summaries did not return candidates")
    if blocks["total_returned"] < 1:
        raise RuntimeError("search_blocks did not return candidates")

    top_block = blocks["candidates"][0]
    lookup = service.lookup_source(
        {
            "doc_id": top_block["source"]["doc_id"],
            "block_id": top_block["source"]["block_id"],
            "block_ref": top_block.get("metadata", {}).get("block_ref"),
        }
    )
    if not lookup.get("found"):
        raise RuntimeError(f"lookup_source did not resolve candidate block: {lookup.get('error')}")

    evidence = service.build_evidence_pack(
        {
            "query": args.query,
            "project_id": args.project_id,
            "document_types": document_types,
            "task_context": {
                "requester": "retrieval-mcp-smoke",
                "knowledge_source": "canonical",
                "canonical_doc_ids": indexed_doc_ids,
            },
        }
    )
    if evidence["status"] != "completed":
        raise RuntimeError(f"build_evidence_pack returned unexpected status: {evidence['status']}")

    payload = {
        "tool_names": service.metadata()["tool_names"],
        "indexed_doc_ids": indexed_doc_ids,
        "embeddings_indexed": indexing_result.embeddings_indexed,
        "summary_candidates": summaries["total_returned"],
        "block_candidates": blocks["total_returned"],
        "summary_backend": summaries["retrieval_backend"],
        "block_backend": blocks["retrieval_backend"],
        "top_summary_source": summaries["candidates"][0]["source"],
        "top_block_ref": top_block.get("metadata", {}).get("block_ref"),
        "lookup_found": lookup["found"],
        "lookup_doc_id": lookup.get("doc_id"),
        "lookup_block_id": lookup.get("block_id"),
        "lookup_source_path": lookup.get("source_path"),
        "build_task_id": evidence["task_id"],
        "build_status": evidence["status"],
        "build_retrieval_backend": evidence["details"].get("retrieval_backend"),
        "build_quality_gate_status": evidence["details"].get("quality_gate_status"),
        "build_unresolved_gaps": evidence["details"].get("unresolved_gaps", []),
        "evidence_blocks": len(evidence["evidence_pack"].get("selected_blocks", [])),
    }
    print(json.dumps(payload, ensure_ascii=False, indent=4))


def _parse_csv(raw: str) -> list[str]:
    return [item.strip() for item in raw.split(",") if item.strip()]


def _build_binary_demo_docs(input_path: Path) -> None:
    output_dir = input_path.parent if input_path.is_file() else input_path
    build_binary_demo_documents(output_dir=output_dir)


if __name__ == "__main__":
    main()
