from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime, timezone
from uuid import uuid4


def normalize_queries(queries: Iterable[str]) -> list[str]:
    normalized = [item.strip() for item in queries if item.strip()]
    return normalized


def chunk_queries(queries: list[str], batch_size: int) -> list[list[str]]:
    if batch_size <= 0:
        raise ValueError("batch_size must be > 0")
    return [queries[index : index + batch_size] for index in range(0, len(queries), batch_size)]


def build_batch_id(prefix: str = "async-batch") -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    return f"{prefix}-{timestamp}-{uuid4().hex[:8]}"

