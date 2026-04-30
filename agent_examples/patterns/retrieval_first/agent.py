from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from agent_examples.common.framework_client import FrameworkClient
from agent_examples.patterns.retrieval_first.config import RetrievalFirstConfig
from agent_examples.patterns.retrieval_first.prompts import DEFAULT_QUERY


@dataclass
class RetrievalFirstAgent:
    """Minimal retrieval-first agent built on top of framework public API."""

    client: FrameworkClient
    config: RetrievalFirstConfig

    def run(self, query: str = DEFAULT_QUERY) -> dict[str, Any]:
        start = self.client.start_retrieval(
            query=query,
            requester=self.config.requester,
            case_dataset_id=self.config.case_dataset_id,
        )
        task_id = str(start["task_id"])

        task = self.client.get_task(task_id)
        evidence = self.client.get_evidence(task_id)

        selected_blocks = evidence.get("evidence_pack", {}).get("selected_blocks", [])
        selected_sources = evidence.get("evidence_pack", {}).get("selected_sources", [])

        return {
            "pattern": "retrieval_first",
            "task_id": task_id,
            "query": query,
            "task_status": task.get("status"),
            "evidence_blocks": len(selected_blocks),
            "top_sources": selected_sources[:3],
        }
