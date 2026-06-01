from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AsyncBatchConfig:
    requester: str = "agent-examples-async-batch"
    case_dataset_id: str = "saa_release_readiness"
    batch_size: int = 2
    continue_on_error: bool = True

