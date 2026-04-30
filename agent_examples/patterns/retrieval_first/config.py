from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RetrievalFirstConfig:
    requester: str = "agent-examples-retrieval"
    case_dataset_id: str = "saa_release_readiness"
