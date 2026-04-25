from __future__ import annotations

import argparse
import json

from apps.api.dependencies import ApiContainer
from infra.fastmcp.template_library_service import FastMcpTemplateLibraryService


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Smoke-проверка Template Library MCP service")
    parser.add_argument("--template-id", default="template-smoke-demo", help="Template id для smoke-проверки")
    parser.add_argument("--version", default="1", help="Версия reusable template")
    parser.add_argument("--draft-version", default="2", help="Дополнительная draft version для governance smoke")
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
            "status": "draft",
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
    published = service.publish_template({"template_id": args.template_id, "version": args.version})
    draft_upserted = service.upsert_template(
        {
            "template_id": args.template_id,
            "version": args.draft_version,
            "status": "draft",
            "sections": [{"section_id": "details", "title": "Details"}],
            "metadata": {"owner": "smoke-test", "lane": "draft"},
        }
    )
    deprecated = service.set_template_status(
        {
            "template_id": args.template_id,
            "version": args.draft_version,
            "status": "deprecated",
            "reason": "smoke deprecation",
            "actor": "smoke-test",
        }
    )
    loaded = service.get_template({"template_id": args.template_id, "version": args.version})
    listed = service.list_templates(
        {"limit": args.limit, "offset": args.offset, "template_id": args.template_id, "status": "published"}
    )
    deprecated_listed = service.list_templates(
        {"limit": args.limit, "offset": args.offset, "template_id": args.template_id, "status": "deprecated"}
    )

    result = {
        "upserted_template_id": upserted["template_id"],
        "upserted_version": upserted["version"],
        "published_status": published["status"],
        "deprecated_version": draft_upserted["version"],
        "deprecated_status": deprecated["status"],
        "loaded_template_id": loaded["template_id"],
        "loaded_status": loaded["status"],
        "loaded_section_id": loaded["template_spec"]["sections"][0]["section_id"],
        "list_total_returned": listed["total_returned"],
        "list_contains_template": any(item["template_id"] == args.template_id for item in listed["items"]),
        "deprecated_total_returned": deprecated_listed["total_returned"],
    }
    print(json.dumps(result, ensure_ascii=False, indent=4))


if __name__ == "__main__":
    main()
