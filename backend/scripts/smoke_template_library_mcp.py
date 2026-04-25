from __future__ import annotations

import argparse
import json

from apps.api.dependencies import ApiContainer
from infra.fastmcp.template_library_service import FastMcpTemplateLibraryService


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Smoke-проверка Template Library MCP service")
    parser.add_argument("--template-id", default="template-smoke-demo", help="Template id для smoke-проверки")
    parser.add_argument("--version", default="1", help="Версия reusable template")
    parser.add_argument("--limit", type=int, default=10, help="Лимит list_templates")
    parser.add_argument("--offset", type=int, default=0, help="Смещение list_templates")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    container = ApiContainer()
    service = FastMcpTemplateLibraryService(container.template_library_service)
    service.register_tools()

    upserted = service.upsert_template(
        {
            "template_id": args.template_id,
            "version": args.version,
            "sections": [
                {
                    "section_id": "overview",
                    "title": "Overview",
                    "objective": "Summarize current status.",
                    "required_keywords": ["status", "summary"],
                }
            ],
            "assembly_rules": [
                {
                    "rule_id": "overview_first",
                    "mode": "section_order",
                    "section_order": ["overview"],
                    "include_writer_draft": False,
                    "include_traceability": True,
                }
            ],
            "metadata": {"owner": "smoke-test"},
        }
    )
    loaded = service.get_template({"template_id": args.template_id, "version": args.version})
    listed = service.list_templates({"limit": args.limit, "offset": args.offset, "template_id": args.template_id})

    result = {
        "upserted_template_id": upserted["template_id"],
        "upserted_version": upserted["version"],
        "loaded_template_id": loaded["template_id"],
        "loaded_section_id": loaded["template_spec"]["sections"][0]["section_id"],
        "list_total_returned": listed["total_returned"],
        "list_contains_template": any(item["template_id"] == args.template_id for item in listed["items"]),
    }
    print(json.dumps(result, ensure_ascii=False, indent=4))


if __name__ == "__main__":
    main()
