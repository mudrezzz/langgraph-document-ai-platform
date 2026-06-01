from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class McpToolFacadeConfig:
    requester: str = "agent-examples-mcp-facade"
    case_dataset_id: str = "saa_release_readiness"
    service_name: str = "example-mcp-facade"
    service_version: str = "v1"

