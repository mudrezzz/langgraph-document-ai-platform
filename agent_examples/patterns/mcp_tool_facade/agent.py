from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from agent_examples.patterns.mcp_tool_facade.config import McpToolFacadeConfig
from agent_examples.patterns.mcp_tool_facade.prompts import DEFAULT_QUERY
from agent_examples.patterns.mcp_tool_facade.tools import (
    build_tool_registry,
    require_text_payload,
    utc_now,
)
from agent_examples.patterns.mcp_tool_facade.workflow import FacadeWorkflowInput, run_facade_retrieval
from agent_examples.patterns.retrieval_first.tools import build_default_filters


@dataclass
class McpToolFacadeCoreAgent:
    """Core agent logic with no MCP transport concerns."""

    config: McpToolFacadeConfig

    def search_evidence(self, *, query: str) -> dict[str, Any]:
        workflow_state = run_facade_retrieval(
            FacadeWorkflowInput(
                query=query,
                filters=build_default_filters(),
                case_dataset_id=self.config.case_dataset_id,
                requester=self.config.requester,
            )
        )
        evidence_pack = workflow_state.evidence_pack
        selected_blocks = [] if evidence_pack is None else evidence_pack.selected_blocks
        selected_sources = [] if evidence_pack is None else evidence_pack.selected_sources
        unresolved_gaps = [] if evidence_pack is None else evidence_pack.unresolved_gaps
        return {
            "query": query,
            "confidence": workflow_state.confidence,
            "evidence_blocks": len(selected_blocks),
            "top_sources": [
                {
                    "doc_id": source.doc_id,
                    "version": source.version,
                    "block_id": source.block_id,
                }
                for source in selected_sources[:3]
            ],
            "unresolved_gaps": unresolved_gaps,
        }


@dataclass
class InProcessMcpToolFacadeAdapter:
    """MCP-style adapter exposing core logic as tool calls."""

    core_agent: McpToolFacadeCoreAgent

    def __post_init__(self) -> None:
        descriptors, handlers = build_tool_registry(
            search_evidence_tool=self.search_evidence_tool,
            get_service_metadata_tool=self.get_service_metadata_tool,
        )
        self._tool_descriptors = descriptors
        self._tool_handlers = handlers

    def metadata(self) -> dict[str, Any]:
        return {
            "service_name": self.core_agent.config.service_name,
            "service_version": self.core_agent.config.service_version,
            "execution_model": "in_process_framework_workflow",
            "tool_names": sorted(self._tool_descriptors.keys()),
            "tool_scopes": {name: descriptor.operation_scope for name, descriptor in self._tool_descriptors.items()},
        }

    def call_tool(self, tool_name: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        if tool_name not in self._tool_handlers:
            raise ValueError(f"Unknown tool `{tool_name}`")
        resolved_payload = {} if payload is None else payload
        result = self._tool_handlers[tool_name](resolved_payload)
        return {
            "tool_name": tool_name,
            "called_at": utc_now(),
            "result": result,
        }

    def search_evidence_tool(self, payload: dict[str, Any]) -> dict[str, Any]:
        query = require_text_payload(payload, "query")
        return self.core_agent.search_evidence(query=query)

    def get_service_metadata_tool(self, _payload: dict[str, Any]) -> dict[str, Any]:
        return self.metadata()


def run_demo_tool_call(query: str = DEFAULT_QUERY) -> dict[str, Any]:
    config = McpToolFacadeConfig()
    core = McpToolFacadeCoreAgent(config=config)
    adapter = InProcessMcpToolFacadeAdapter(core_agent=core)
    return {
        "pattern": "mcp_tool_facade",
        "execution_model": "in_process_framework_workflow",
        "adapter_kind": "in_process_mcp_style_facade",
        "service": adapter.metadata(),
        "tool_invocation": adapter.call_tool("search_evidence", {"query": query}),
    }

