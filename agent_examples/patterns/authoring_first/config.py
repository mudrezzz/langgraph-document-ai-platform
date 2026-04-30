from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AuthoringFirstConfig:
    requester: str = "agent-examples-authoring"
    case_dataset_id: str = "saa_release_readiness"
    workflow_mode: str = "multi_step"
    draft_strategy: str = "deterministic"
    artifact_title: str = "Agent Examples: Policy Brief"
