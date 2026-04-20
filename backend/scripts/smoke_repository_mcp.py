from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from uuid import uuid4

from apps.api.dependencies import ApiContainer
from infra.fastmcp.repository_service import FastMcpRepositoryService


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Smoke-проверка Repository MCP service")
    parser.add_argument("--prefix", default="repo-smoke", help="Префикс для doc_id тестовых документов")
    parser.add_argument("--limit", type=int, default=10, help="Лимит list_documents")
    parser.add_argument("--offset", type=int, default=0, help="Смещение list_documents")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    container = ApiContainer()
    service = FastMcpRepositoryService(container.document_service)
    service.register_tools()

    doc_id_1 = f"{args.prefix}-{uuid4()}"
    doc_id_2 = f"{args.prefix}-{uuid4()}"

    upsert_1 = service.upsert_document(
        {
            "doc_id": doc_id_1,
            "payload": {
                "title": "Release Decision",
                "project_id": "p1",
                "status": "draft",
                "updated_at": datetime.now(timezone.utc).isoformat(),
            },
        }
    )
    upsert_2 = service.upsert_document(
        {
            "doc_id": doc_id_2,
            "payload": {
                "title": "Security Checklist",
                "project_id": "p1",
                "status": "approved",
                "updated_at": datetime.now(timezone.utc).isoformat(),
            },
        }
    )
    loaded_1 = service.get_document({"doc_id": doc_id_1})
    listed = service.list_documents({"limit": args.limit, "offset": args.offset})

    listed_ids = {item["doc_id"] for item in listed["items"]}
    result = {
        "upserted_doc_ids": [upsert_1["doc_id"], upsert_2["doc_id"]],
        "loaded_doc_id": loaded_1["doc_id"],
        "loaded_title": loaded_1["payload"].get("title"),
        "list_total_returned": listed["total_returned"],
        "list_contains_doc_1": doc_id_1 in listed_ids,
        "list_contains_doc_2": doc_id_2 in listed_ids,
    }
    print(json.dumps(result, ensure_ascii=False, indent=4))


if __name__ == "__main__":
    main()
