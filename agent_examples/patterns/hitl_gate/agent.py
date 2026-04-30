from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

from agent_examples.common.framework_client import FrameworkClient
from agent_examples.patterns.hitl_gate.config import HitlGateConfig
from agent_examples.patterns.hitl_gate.prompts import DEFAULT_QUERY


@dataclass
class HitlGateAgent:
    """Async/HITL agent showing reviewer loop over framework API."""

    client: FrameworkClient
    config: HitlGateConfig
    poll_interval_sec: float = 0.5
    poll_timeout_sec: int = 120

    def _wait_for_status(self, task_id: str, expected: set[str]) -> dict[str, Any]:
        deadline = time.time() + self.poll_timeout_sec
        last: dict[str, Any] = {}
        while time.time() < deadline:
            last = self.client.get_task(task_id)
            status = str(last.get("status", ""))
            if status in expected:
                return last
            time.sleep(self.poll_interval_sec)
        raise TimeoutError(f"Task {task_id} did not reach {expected}. last={last}")

    def run(self, query: str = DEFAULT_QUERY, decisions: list[str] | None = None) -> dict[str, Any]:
        if decisions is None:
            decisions = ["needs_changes", "approve"]

        start = self.client.start_authoring_async(
            query=query,
            requester=self.config.requester,
            case_dataset_id=self.config.case_dataset_id,
            workflow_mode=self.config.workflow_mode,
            draft_strategy=self.config.draft_strategy,
            artifact_title=self.config.artifact_title,
            hitl_required=self.config.hitl_required,
        )
        task_id = str(start["task_id"])
        task = self._wait_for_status(task_id, {"waiting_human", "completed", "failed"})

        history: list[dict[str, Any]] = []
        while task.get("status") == "waiting_human":
            if not decisions:
                raise RuntimeError("Task still waiting_human but decision list is exhausted.")
            decision = decisions.pop(0)
            hitl_state = self.client.get_hitl_status(task_id)
            iteration = int(hitl_state.get("current_iteration", 1))
            self.client.submit_hitl_review(
                task_id=task_id,
                decision=decision,
                expected_iteration=iteration,
                idempotency_key=f"agent-examples-{task_id}-{iteration}-{decision}",
            )
            history.append({"iteration": iteration, "decision": decision})
            task = self._wait_for_status(task_id, {"waiting_human", "completed", "failed"})

        artifact = self.client.get_artifact(task_id) if task.get("status") == "completed" else {}

        return {
            "pattern": "hitl_gate",
            "task_id": task_id,
            "query": query,
            "task_status": task.get("status"),
            "hitl_decisions_applied": history,
            "artifact_id": artifact.get("artifact_id"),
            "artifact_title": artifact.get("title"),
        }
