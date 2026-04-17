from __future__ import annotations

from pathlib import Path

from domain_rag.retrieval.datasets import DEFAULT_CASE_DATASET_ID, load_case_dataset, resolve_case_dataset_path


def test_case_dataset_loader_default() -> None:
    summary, detail = load_case_dataset()

    assert len(summary) >= 1
    assert len(detail) >= 1


def test_case_dataset_loader_by_id() -> None:
    summary, detail = load_case_dataset(dataset_id=DEFAULT_CASE_DATASET_ID)

    assert any(block.source.doc_id == "METH-001" for block in summary)
    assert any(block.source.doc_id == "INT-015" for block in detail)


def test_case_dataset_resolve_path_exists() -> None:
    path = resolve_case_dataset_path(DEFAULT_CASE_DATASET_ID)

    assert isinstance(path, Path)
    assert path.exists()