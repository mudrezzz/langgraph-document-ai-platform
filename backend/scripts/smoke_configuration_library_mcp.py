from __future__ import annotations

import argparse
import json

from apps.api.dependencies import ApiContainer
from infra.fastmcp.configuration_library_service import FastMcpConfigurationLibraryService


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Smoke-проверка Configuration Library MCP service")
    parser.add_argument("--config-id", default="retrieval-policy-demo", help="Configuration id для smoke-проверки")
    parser.add_argument("--version", default="1", help="Базовая версия конфигурации")
    parser.add_argument("--next-version", default="2", help="Вторая версия конфигурации для compare")
    parser.add_argument("--limit", type=int, default=10, help="Лимит list/find")
    parser.add_argument("--offset", type=int, default=0, help="Смещение list/find")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    container = ApiContainer()
    service = FastMcpConfigurationLibraryService(container.configuration_library_service)
    service.register_tools()

    service.upsert_config(
        {
            "config_id": args.config_id,
            "version": args.version,
            "config_type": "retrieval_policy",
            "title": "Base Retrieval Policy",
            "payload": {
                "retrieval": {"top_k": 8, "rerank": True},
                "quality_gates": {"min_sources": 3, "require_source_mapping": True},
            },
            "metadata": {"owner": "smoke-test"},
            "tags": ["release", "prod", "retrieval"],
        }
    )
    updated = service.upsert_config(
        {
            "config_id": args.config_id,
            "version": args.next_version,
            "config_type": "retrieval_policy",
            "title": "Updated Retrieval Policy",
            "payload": {
                "retrieval": {"top_k": 10, "rerank": True},
                "quality_gates": {"min_sources": 4, "require_source_mapping": True},
            },
            "metadata": {"owner": "smoke-test", "lane": "candidate"},
            "tags": ["release", "prod", "retrieval"],
        }
    )
    service.upsert_config(
        {
            "config_id": f"{args.config_id}-similar",
            "version": "1",
            "config_type": "retrieval_policy",
            "title": "Similar Retrieval Policy",
            "payload": {
                "retrieval": {"top_k": 9, "rerank": True},
                "quality_gates": {"min_sources": 4, "require_source_mapping": True},
            },
            "metadata": {"owner": "smoke-test", "lane": "peer"},
            "tags": ["release", "prod", "retrieval"],
        }
    )

    loaded = service.get_config({"config_id": args.config_id})
    listed = service.list_configs(
        {
            "limit": args.limit,
            "offset": args.offset,
            "config_type": "retrieval_policy",
            "tag": "release",
        }
    )
    similar = service.find_similar_configs(
        {
            "reference_config_id": args.config_id,
            "reference_version": args.next_version,
            "limit": args.limit,
            "offset": args.offset,
        }
    )
    comparison = service.compare_configs(
        {
            "left_config_id": args.config_id,
            "left_version": args.version,
            "right_config_id": args.config_id,
            "right_version": args.next_version,
        }
    )

    result = {
        "tool_names": service.metadata()["tool_names"],
        "loaded_config_id": loaded["config_id"],
        "loaded_version": loaded["version"],
        "updated_version": updated["version"],
        "list_total_returned": listed["total_returned"],
        "list_contains_config": any(item["config_id"] == args.config_id for item in listed["items"]),
        "similar_total_returned": similar["total_returned"],
        "top_similar_config_id": similar["items"][0]["config_id"] if similar["items"] else None,
        "top_similarity_score": similar["items"][0]["similarity_score"] if similar["items"] else None,
        "compare_changed_keys": [item["key"] for item in comparison["changed_values"]],
        "compare_shared_keys": len(comparison["shared_keys"]),
    }
    print(json.dumps(result, ensure_ascii=False, indent=4))


if __name__ == "__main__":
    main()
