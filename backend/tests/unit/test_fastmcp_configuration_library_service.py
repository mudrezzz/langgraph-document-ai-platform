from __future__ import annotations

import pytest

from application.configuration_library_service import ConfigurationLibraryApplicationService
from infra.fastmcp.configuration_library_service import FastMcpConfigurationLibraryService
from infra.postgres.configuration_store import PostgresConfigurationStore


def _build_service() -> FastMcpConfigurationLibraryService:
    app_service = ConfigurationLibraryApplicationService(
        PostgresConfigurationStore(dsn=None, use_fallback_if_unset=True)
    )
    service = FastMcpConfigurationLibraryService(app_service)
    service.register_tools()
    return service


def test_fastmcp_configuration_library_service_metadata_contains_tools() -> None:
    service = _build_service()

    metadata = service.metadata()

    assert metadata["service_name"] == "configuration-library-mcp"
    assert metadata["transport"] == "fastmcp"
    assert metadata["policy_version"] == "mcp-policy-v1"
    assert metadata["service_scope"] == "configuration-library"
    assert metadata["operation_scopes"] == {"compare_configs": "read", "find_similar_configs": "read", "get_config": "read", "list_configs": "read", "upsert_config": "write"}
    assert metadata["tool_required_roles"] == {
        "compare_configs": [],
        "find_similar_configs": [],
        "get_config": [],
        "list_configs": [],
        "upsert_config": ["config_admin"],
    }
    assert "upsert_config" in metadata["tool_names"]
    assert "get_config" in metadata["tool_names"]
    assert "list_configs" in metadata["tool_names"]
    assert "find_similar_configs" in metadata["tool_names"]
    assert "compare_configs" in metadata["tool_names"]


def test_fastmcp_configuration_library_service_upsert_get_list() -> None:
    service = _build_service()

    upserted = service.upsert_config(
        {
            "config_id": "release_policy",
            "version": "1",
            "config_type": "retrieval_policy",
            "title": "Release Retrieval Policy",
            "payload": {
                "retrieval": {"top_k": 8, "rerank": True},
                "quality_gates": {"min_sources": 3},
            },
            "metadata": {"owner": "platform"},
            "tags": ["release", "prod"],
        }
    )
    loaded = service.get_config({"config_id": "release_policy", "version": "1"})
    listed = service.list_configs({"limit": 10, "offset": 0, "config_type": "retrieval_policy"})

    assert upserted["config_id"] == "release_policy"
    assert upserted["config_type"] == "retrieval_policy"
    assert loaded["payload"]["retrieval"]["top_k"] == 8
    assert listed["total_returned"] == 1
    assert listed["items"][0]["config_id"] == "release_policy"


def test_fastmcp_configuration_library_service_find_similar_configs_returns_ranked_matches() -> None:
    service = _build_service()
    service.upsert_config(
        {
            "config_id": "policy-a",
            "version": "1",
            "config_type": "retrieval_policy",
            "payload": {"retrieval": {"top_k": 10, "rerank": True}, "quality": {"min_sources": 3}},
            "tags": ["release", "prod"],
        }
    )
    service.upsert_config(
        {
            "config_id": "policy-b",
            "version": "1",
            "config_type": "retrieval_policy",
            "payload": {"retrieval": {"top_k": 10, "rerank": True}, "quality": {"min_sources": 2}},
            "tags": ["release", "prod"],
        }
    )
    service.upsert_config(
        {
            "config_id": "policy-c",
            "version": "1",
            "config_type": "retrieval_policy",
            "payload": {"retrieval": {"top_k": 3, "rerank": False}},
            "tags": ["draft"],
        }
    )

    result = service.find_similar_configs({"reference_config_id": "policy-a", "reference_version": "1", "limit": 5})

    assert result["total_returned"] == 2
    assert result["items"][0]["config_id"] == "policy-b"
    assert result["items"][0]["similarity_score"] >= result["items"][1]["similarity_score"]
    assert "release" in result["items"][0]["overlapping_tags"]


def test_fastmcp_configuration_library_service_compare_configs_returns_changed_paths() -> None:
    service = _build_service()
    service.upsert_config(
        {
            "config_id": "policy-base",
            "version": "1",
            "config_type": "retrieval_policy",
            "payload": {"retrieval": {"top_k": 6, "rerank": True}, "quality": {"min_sources": 2}},
        }
    )
    service.upsert_config(
        {
            "config_id": "policy-next",
            "version": "1",
            "config_type": "retrieval_policy",
            "payload": {"retrieval": {"top_k": 8, "rerank": True}, "quality": {"min_sources": 2}},
        }
    )

    result = service.compare_configs({"left_config_id": "policy-base", "right_config_id": "policy-next"})

    assert "retrieval.top_k" in result["shared_keys"]
    assert result["changed_values"][0]["key"] == "retrieval.top_k"
    assert result["changed_values"][0]["left_value"] == 6
    assert result["changed_values"][0]["right_value"] == 8


def test_fastmcp_configuration_library_service_get_not_found_raises_value_error() -> None:
    service = _build_service()

    with pytest.raises(ValueError, match="missing-config"):
        service.get_config({"config_id": "missing-config"})


def test_fastmcp_configuration_library_service_upsert_requires_role_when_auth_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_AUTH_ENABLED", "1")
    service = _build_service()

    with pytest.raises(ValueError, match="Authentication required"):
        service.upsert_config({"config_id": "cfg-1", "payload": {"k": "v"}})

    result = service.upsert_config(
        {
            "config_id": "cfg-1",
            "payload": {"k": "v"},
            "actor": "alice",
            "roles": ["config_admin"],
        }
    )

    assert result["config_id"] == "cfg-1"
