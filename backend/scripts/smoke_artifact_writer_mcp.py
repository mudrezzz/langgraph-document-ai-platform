from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from uuid import uuid4

from apps.api.dependencies import ApiContainer
from infra.fastmcp.artifact_writer_service import FastMcpArtifactWriterService


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Smoke-проверка Artifact Writer MCP service")
    parser.add_argument("--prefix", default="artifact-smoke", help="Префикс для artifact_id тестовых артефактов")
    parser.add_argument("--limit", type=int, default=10, help="Лимит list_artifacts")
    parser.add_argument("--offset", type=int, default=0, help="Смещение list_artifacts")
    parser.add_argument("--artifact-type", default="release_report", help="Тип тестового артефакта")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    container = ApiContainer()
    service = FastMcpArtifactWriterService(container.artifact_service)
    service.register_tools()

    artifact_id_1 = f"{args.prefix}-{uuid4()}"
    artifact_id_2 = f"{args.prefix}-{uuid4()}"

    write_1 = service.write_artifact(
        {
            "artifact_id": artifact_id_1,
            "artifact_type": args.artifact_type,
            "title": "Release Readiness Report",
            "content": "# GO/NO-GO\n- blockers: 0\n- approvals: 2/2",
            "format": "markdown",
            "metadata": {"project_id": "p1", "generated_at": datetime.now(timezone.utc).isoformat()},
        }
    )
    write_2 = service.write_artifact(
        {
            "artifact_id": artifact_id_2,
            "artifact_type": args.artifact_type,
            "title": "Traceability Map",
            "content": "REQ-001 -> SRC-7",
            "format": "text",
            "metadata": {"project_id": "p1", "generated_at": datetime.now(timezone.utc).isoformat()},
        }
    )
    loaded_1 = service.get_artifact({"artifact_id": artifact_id_1})
    listed = service.list_artifacts(
        {
            "limit": args.limit,
            "offset": args.offset,
            "artifact_type": args.artifact_type,
        }
    )

    listed_ids = {item["artifact_id"] for item in listed["items"]}
    result = {
        "written_artifact_ids": [write_1["artifact_id"], write_2["artifact_id"]],
        "loaded_artifact_id": loaded_1["artifact_id"],
        "loaded_title": loaded_1["title"],
        "list_total_returned": listed["total_returned"],
        "list_contains_artifact_1": artifact_id_1 in listed_ids,
        "list_contains_artifact_2": artifact_id_2 in listed_ids,
    }
    print(json.dumps(result, ensure_ascii=False, indent=4))


if __name__ == "__main__":
    main()
