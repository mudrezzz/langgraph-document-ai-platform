from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from agent_examples.common.framework_client import FrameworkClient
from agent_examples.patterns.authoring_first.config import AuthoringFirstConfig
from agent_examples.patterns.authoring_first.prompts import DEFAULT_QUERY


@dataclass
class AuthoringFirstAgent:
    """Minimal authoring-first agent based on framework public authoring endpoint."""

    client: FrameworkClient
    config: AuthoringFirstConfig

    def run(self, query: str = DEFAULT_QUERY) -> dict[str, Any]:
        start = self.client.start_authoring(
            query=query,
            requester=self.config.requester,
            case_dataset_id=self.config.case_dataset_id,
            workflow_mode=self.config.workflow_mode,
            draft_strategy=self.config.draft_strategy,
            artifact_title=self.config.artifact_title,
        )
        task_id = str(start["task_id"])

        task = self.client.get_task(task_id)
        artifact = self.client.get_artifact(task_id)

        metadata = artifact.get("metadata", {})
        return {
            "pattern": "authoring_first",
            "task_id": task_id,
            "query": query,
            "task_status": task.get("status"),
            "artifact_id": artifact.get("artifact_id"),
            "artifact_title": artifact.get("title"),
            "workflow_mode": metadata.get("workflow_mode"),
            "steps_total": len(metadata.get("steps_summary", [])),
            "traceability_sections": len(artifact.get("traceability", {}).get("sections", [])),
        }
