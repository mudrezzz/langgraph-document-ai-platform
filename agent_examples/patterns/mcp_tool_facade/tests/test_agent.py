from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from agent_examples.common.path_setup import ensure_backend_paths

ensure_backend_paths(repo_root=REPO_ROOT)

from agent_examples.patterns.mcp_tool_facade.agent import (
    InProcessMcpToolFacadeAdapter,
    McpToolFacadeCoreAgent,
    run_demo_tool_call,
)
from agent_examples.patterns.mcp_tool_facade.config import McpToolFacadeConfig
from schemas.rag.contracts import EvidencePack, RetrievalFilter, RerankedBlock, SourceRef
from schemas.workflow.states import RetrievalWorkflowState


def test_facade_calls_core_logic(monkeypatch) -> None:
    sample_state = RetrievalWorkflowState(
        query="q",
        filters=RetrievalFilter(project_id="p1"),
        confidence=0.91,
        unresolved_gaps=[],
        evidence_pack=EvidencePack(
            selected_sources=[SourceRef(doc_id="D1", version="v1", block_id="b1")],
            selected_blocks=[
                RerankedBlock(
                    text="t",
                    source=SourceRef(doc_id="D1", version="v1", block_id="b1"),
                    score=0.91,
                )
            ],
            unresolved_gaps=[],
            confidence_notes=["ok"],
        ),
    )

    monkeypatch.setattr(
        "agent_examples.patterns.mcp_tool_facade.agent.run_facade_retrieval",
        lambda _payload: sample_state,
    )

    core = McpToolFacadeCoreAgent(config=McpToolFacadeConfig())
    adapter = InProcessMcpToolFacadeAdapter(core_agent=core)
    response = adapter.call_tool("search_evidence", {"query": "q"})

    assert response["tool_name"] == "search_evidence"
    assert response["result"]["evidence_blocks"] == 1
    assert response["result"]["top_sources"][0]["doc_id"] == "D1"


def test_facade_rejects_unknown_tool() -> None:
    core = McpToolFacadeCoreAgent(config=McpToolFacadeConfig())
    adapter = InProcessMcpToolFacadeAdapter(core_agent=core)
    with pytest.raises(ValueError):
        adapter.call_tool("unknown_tool", {})


def test_mcp_tool_facade_in_process_smoke() -> None:
    payload = run_demo_tool_call()
    assert payload["pattern"] == "mcp_tool_facade"
    assert payload["execution_model"] == "in_process_framework_workflow"
    assert payload["tool_invocation"]["tool_name"] == "search_evidence"

