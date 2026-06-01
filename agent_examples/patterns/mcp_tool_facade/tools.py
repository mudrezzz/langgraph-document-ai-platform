from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True)
class ToolDescriptor:
    name: str
    description: str
    operation_scope: str


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def require_text_payload(payload: dict[str, Any], field_name: str) -> str:
    raw = payload.get(field_name, "")
    if not isinstance(raw, str) or not raw.strip():
        raise ValueError(f"payload must include non-empty string field `{field_name}`")
    return raw.strip()


def build_tool_registry(
    *,
    search_evidence_tool: Callable[[dict[str, Any]], dict[str, Any]],
    get_service_metadata_tool: Callable[[dict[str, Any]], dict[str, Any]],
) -> tuple[dict[str, ToolDescriptor], dict[str, Callable[[dict[str, Any]], dict[str, Any]]]]:
    descriptors = {
        "search_evidence": ToolDescriptor(
            name="search_evidence",
            description="Retrieve evidence pack for a query using core in-process agent logic.",
            operation_scope="action",
        ),
        "get_service_metadata": ToolDescriptor(
            name="get_service_metadata",
            description="Return facade metadata and available tools.",
            operation_scope="read",
        ),
    }
    handlers = {
        "search_evidence": search_evidence_tool,
        "get_service_metadata": get_service_metadata_tool,
    }
    return descriptors, handlers

