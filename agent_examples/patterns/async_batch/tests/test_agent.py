from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from agent_examples.common.path_setup import ensure_backend_paths

ensure_backend_paths(repo_root=REPO_ROOT)

from agent_examples.patterns.async_batch.agent import AsyncBatchAgent
from agent_examples.patterns.async_batch.config import AsyncBatchConfig
from agent_examples.patterns.async_batch.workflow import (
    AsyncBatchItemResult,
    AsyncBatchWorkflowResult,
)


def test_async_batch_agent_formats_workflow_result(monkeypatch) -> None:
    sample_result = AsyncBatchWorkflowResult(
        batch_id="batch-1",
        execution_model="in_process_framework_workflow",
        started_at="2026-06-02T10:00:00+00:00",
        completed_at="2026-06-02T10:00:02+00:00",
        total_queries=2,
        completed_queries=1,
        failed_queries=1,
        items=[
            AsyncBatchItemResult(
                item_index=0,
                batch_index=0,
                query="q1",
                status="completed",
                confidence=0.8,
                evidence_blocks=2,
                unresolved_gaps=[],
                top_sources=[{"doc_id": "D1", "version": "v1", "block_id": "b1"}],
            ),
            AsyncBatchItemResult(
                item_index=1,
                batch_index=0,
                query="q2",
                status="failed",
                confidence=0.0,
                evidence_blocks=0,
                unresolved_gaps=[],
                top_sources=[],
                error="boom",
            ),
        ],
    )

    monkeypatch.setattr(
        "agent_examples.patterns.async_batch.agent.run_async_batch_workflow",
        lambda _payload: sample_result,
    )

    agent = AsyncBatchAgent(config=AsyncBatchConfig())
    result = agent.run(queries=["q1", "q2"])

    assert result["pattern"] == "async_batch"
    assert result["execution_model"] == "in_process_framework_workflow"
    assert result["failed_queries"] == 1
    assert result["items"][0]["top_sources"][0]["doc_id"] == "D1"


def test_async_batch_agent_in_process_smoke() -> None:
    agent = AsyncBatchAgent(config=AsyncBatchConfig(batch_size=2))
    result = agent.run()
    assert result["pattern"] == "async_batch"
    assert result["execution_model"] == "in_process_framework_workflow"
    assert result["total_queries"] >= 1
    assert result["completed_queries"] >= 1

