from __future__ import annotations

from typing import Any, Callable

from application.configuration_library_service import ConfigurationLibraryApplicationService
from application.errors import ConfigurationNotFoundError
from framework.mcp import BaseFastMcpService
from schemas.mcp.configuration_library import (
    ConfigurationLibraryMcpCompareConfigsInput,
    ConfigurationLibraryMcpCompareConfigsOutput,
    ConfigurationLibraryMcpConfigItem,
    ConfigurationLibraryMcpFindSimilarConfigsInput,
    ConfigurationLibraryMcpFindSimilarConfigsOutput,
    ConfigurationLibraryMcpGetConfigInput,
    ConfigurationLibraryMcpGetConfigOutput,
    ConfigurationLibraryMcpListConfigsInput,
    ConfigurationLibraryMcpListConfigsOutput,
    ConfigurationLibraryMcpSimilarConfigItem,
    ConfigurationLibraryMcpUpsertConfigInput,
    ConfigurationLibraryMcpUpsertConfigOutput,
)


class FastMcpConfigurationLibraryService(BaseFastMcpService):
    """FastMCP boundary for versioned configuration library operations."""

    def __init__(self, configuration_library_service: ConfigurationLibraryApplicationService) -> None:
        super().__init__(service_name="configuration-library-mcp", version="0.1.0")
        self._configuration_library_service = configuration_library_service
        self._tools: dict[str, Callable[..., Any]] = {}

    def register_tools(self) -> None:
        self._tools = {
            "upsert_config": self.upsert_config,
            "get_config": self.get_config,
            "list_configs": self.list_configs,
            "find_similar_configs": self.find_similar_configs,
            "compare_configs": self.compare_configs,
        }

    def metadata(self) -> dict[str, Any]:
        payload = super().metadata()
        payload["tool_names"] = sorted(self._tools.keys())
        return payload

    def upsert_config(self, payload: ConfigurationLibraryMcpUpsertConfigInput | dict[str, Any]) -> dict[str, Any]:
        validated = ConfigurationLibraryMcpUpsertConfigInput.model_validate(payload)
        saved = self._configuration_library_service.upsert_config(
            config_id=validated.config_id,
            version=validated.version,
            config_type=validated.config_type,
            title=validated.title,
            payload=validated.payload,
            metadata=validated.metadata,
            tags=validated.tags,
        )
        response = ConfigurationLibraryMcpUpsertConfigOutput.model_validate(saved.model_dump(mode="json"))
        return response.model_dump(mode="json")

    def get_config(self, payload: ConfigurationLibraryMcpGetConfigInput | dict[str, Any]) -> dict[str, Any]:
        validated = ConfigurationLibraryMcpGetConfigInput.model_validate(payload)
        try:
            loaded = self._configuration_library_service.get_config(validated.config_id, validated.version)
        except ConfigurationNotFoundError as exc:
            raise ValueError(str(exc)) from exc
        response = ConfigurationLibraryMcpGetConfigOutput.model_validate(loaded.model_dump(mode="json"))
        return response.model_dump(mode="json")

    def list_configs(self, payload: ConfigurationLibraryMcpListConfigsInput | dict[str, Any] | None = None) -> dict[str, Any]:
        validated = ConfigurationLibraryMcpListConfigsInput.model_validate(payload or {})
        page = self._configuration_library_service.list_configs(
            limit=validated.limit,
            offset=validated.offset,
            config_id=validated.config_id,
            config_type=validated.config_type,
            tag=validated.tag,
        )
        response = ConfigurationLibraryMcpListConfigsOutput(
            items=[ConfigurationLibraryMcpConfigItem.model_validate(item.model_dump(mode="json")) for item in page.items],
            limit=page.limit,
            offset=page.offset,
            total_returned=page.total_returned,
        )
        return response.model_dump(mode="json")

    def find_similar_configs(
        self,
        payload: ConfigurationLibraryMcpFindSimilarConfigsInput | dict[str, Any],
    ) -> dict[str, Any]:
        validated = ConfigurationLibraryMcpFindSimilarConfigsInput.model_validate(payload)
        try:
            page = self._configuration_library_service.find_similar_configs(
                reference_config_id=validated.reference_config_id,
                reference_version=validated.reference_version,
                candidate_payload=validated.candidate_payload,
                config_type=validated.config_type,
                tags=validated.tags,
                limit=validated.limit,
                offset=validated.offset,
            )
        except ConfigurationNotFoundError as exc:
            raise ValueError(str(exc)) from exc
        response = ConfigurationLibraryMcpFindSimilarConfigsOutput(
            items=[
                ConfigurationLibraryMcpSimilarConfigItem.model_validate(item.model_dump(mode="json"))
                for item in page.items
            ],
            limit=page.limit,
            offset=page.offset,
            total_returned=page.total_returned,
        )
        return response.model_dump(mode="json")

    def compare_configs(self, payload: ConfigurationLibraryMcpCompareConfigsInput | dict[str, Any]) -> dict[str, Any]:
        validated = ConfigurationLibraryMcpCompareConfigsInput.model_validate(payload)
        try:
            comparison = self._configuration_library_service.compare_configs(
                left_config_id=validated.left_config_id,
                right_config_id=validated.right_config_id,
                left_version=validated.left_version,
                right_version=validated.right_version,
            )
        except ConfigurationNotFoundError as exc:
            raise ValueError(str(exc)) from exc
        response = ConfigurationLibraryMcpCompareConfigsOutput.model_validate(comparison.model_dump(mode="json"))
        return response.model_dump(mode="json")


def create_fastmcp_configuration_library_server(service: FastMcpConfigurationLibraryService) -> Any:
    """Create FastMCP runtime server for configuration library boundary."""

    try:
        from fastmcp import FastMCP
    except Exception as exc:  # pragma: no cover
        raise RuntimeError(
            "Не удалось импортировать fastmcp. Установите пакет `fastmcp` для запуска MCP-сервиса."
        ) from exc

    service.register_tools()
    server = FastMCP("configuration-library-mcp")

    @server.tool()
    def upsert_config(
        config_id: str,
        version: str = "1",
        config_type: str = "generic",
        title: str | None = None,
        payload: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
        tags: list[str] | None = None,
    ) -> dict[str, Any]:
        """MCP tool: upsert_config."""

        return service.upsert_config(
            {
                "config_id": config_id,
                "version": version,
                "config_type": config_type,
                "title": title,
                "payload": payload or {},
                "metadata": metadata or {},
                "tags": tags or [],
            }
        )

    @server.tool()
    def get_config(config_id: str, version: str | None = None) -> dict[str, Any]:
        """MCP tool: get_config."""

        return service.get_config({"config_id": config_id, "version": version})

    @server.tool()
    def list_configs(
        limit: int = 20,
        offset: int = 0,
        config_id: str | None = None,
        config_type: str | None = None,
        tag: str | None = None,
    ) -> dict[str, Any]:
        """MCP tool: list_configs."""

        return service.list_configs(
            {
                "limit": limit,
                "offset": offset,
                "config_id": config_id,
                "config_type": config_type,
                "tag": tag,
            }
        )

    @server.tool()
    def find_similar_configs(
        reference_config_id: str | None = None,
        reference_version: str | None = None,
        candidate_payload: dict[str, Any] | None = None,
        config_type: str | None = None,
        tags: list[str] | None = None,
        limit: int = 10,
        offset: int = 0,
    ) -> dict[str, Any]:
        """MCP tool: find_similar_configs."""

        return service.find_similar_configs(
            {
                "reference_config_id": reference_config_id,
                "reference_version": reference_version,
                "candidate_payload": candidate_payload,
                "config_type": config_type,
                "tags": tags or [],
                "limit": limit,
                "offset": offset,
            }
        )

    @server.tool()
    def compare_configs(
        left_config_id: str,
        right_config_id: str,
        left_version: str | None = None,
        right_version: str | None = None,
    ) -> dict[str, Any]:
        """MCP tool: compare_configs."""

        return service.compare_configs(
            {
                "left_config_id": left_config_id,
                "right_config_id": right_config_id,
                "left_version": left_version,
                "right_version": right_version,
            }
        )

    return server
