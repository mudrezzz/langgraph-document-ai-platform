from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class HitlGateConfig:
    requester: str = "agent-examples-hitl"
    case_dataset_id: str = "saa_release_readiness"
    template_id: str = "release_readiness"
    workflow_mode: str = "multi_step"
    draft_strategy: str = "deterministic"
    artifact_title: str = "Agent Examples: HITL Review"
    artifact_format: str = "markdown"
    hitl_required: bool = True
    hitl_max_iterations: int = 3
