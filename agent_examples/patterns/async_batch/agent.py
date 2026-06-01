from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from agent_examples.patterns.async_batch.config import AsyncBatchConfig
from agent_examples.patterns.async_batch.prompts import DEFAULT_QUERIES
from agent_examples.patterns.async_batch.workflow import AsyncBatchWorkflowInput, run_async_batch_workflow
from agent_examples.patterns.retrieval_first.tools import build_default_filters


@dataclass
class AsyncBatchAgent:
    """In-process batch retrieval agent for long-running style workloads."""

    config: AsyncBatchConfig

    def run(self, queries: list[str] | None = None) -> dict[str, Any]:
        effective_queries = DEFAULT_QUERIES if queries is None else queries
        workflow_result = run_async_batch_workflow(
            AsyncBatchWorkflowInput(
                queries=effective_queries,
                filters=build_default_filters(),
                case_dataset_id=self.config.case_dataset_id,
                requester=self.config.requester,
                batch_size=self.config.batch_size,
                continue_on_error=self.config.continue_on_error,
            )
        )
        average_confidence = 0.0
        completed_items = [item for item in workflow_result.items if item.status == "completed"]
        if completed_items:
            average_confidence = sum(item.confidence for item in completed_items) / len(completed_items)

        return {
            "pattern": "async_batch",
            "execution_model": workflow_result.execution_model,
            "batch_id": workflow_result.batch_id,
            "case_dataset_id": self.config.case_dataset_id,
            "batch_size": self.config.batch_size,
            "continue_on_error": self.config.continue_on_error,
            "started_at": workflow_result.started_at,
            "completed_at": workflow_result.completed_at,
            "total_queries": workflow_result.total_queries,
            "completed_queries": workflow_result.completed_queries,
            "failed_queries": workflow_result.failed_queries,
            "average_confidence": round(average_confidence, 4),
            "items": [asdict(item) for item in workflow_result.items],
        }

