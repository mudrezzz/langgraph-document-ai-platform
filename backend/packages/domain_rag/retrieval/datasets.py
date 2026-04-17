from __future__ import annotations

import json
from pathlib import Path

from schemas.rag.contracts import RetrievedBlock

DEFAULT_CASE_DATASET_ID = "saa_release_readiness"


def resolve_case_dataset_path(dataset_id: str) -> Path:
    """Возвращает путь к JSON датасету тестового бизнес-кейса."""

    base = Path(__file__).resolve().parents[3] / "examples" / "cases"

    mapping = {
        "saa_release_readiness": base / "saa_release_readiness_case" / "input" / "knowledge_layers.json",
    }

    if dataset_id not in mapping:
        raise KeyError(f"Неизвестный case dataset id: {dataset_id}")

    return mapping[dataset_id]


def load_case_dataset(
    *,
    dataset_id: str | None = None,
    dataset_path: str | None = None,
) -> tuple[list[RetrievedBlock], list[RetrievedBlock]]:
    """Загружает summary/detail блоки для retrieval workflow из JSON датасета."""

    if dataset_path:
        path = Path(dataset_path)
    else:
        normalized_id = dataset_id or DEFAULT_CASE_DATASET_ID
        path = resolve_case_dataset_path(normalized_id)

    if not path.exists():
        raise FileNotFoundError(f"Файл датасета не найден: {path}")

    payload = json.loads(path.read_text(encoding="utf-8"))

    summary_blocks = [RetrievedBlock.model_validate(item) for item in payload.get("summary_blocks", [])]
    detail_blocks = [RetrievedBlock.model_validate(item) for item in payload.get("detail_blocks", [])]

    if not summary_blocks and not detail_blocks:
        raise ValueError("Датасет не содержит summary_blocks или detail_blocks")

    return summary_blocks, detail_blocks