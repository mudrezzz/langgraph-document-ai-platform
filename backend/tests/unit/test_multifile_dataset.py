from __future__ import annotations

from pathlib import Path

from domain_rag.retrieval.multifile_dataset import load_multifile_case_dataset


def test_load_multifile_case_dataset_from_release_case_dir() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    dataset_dir = repo_root / "backend" / "examples" / "cases" / "release_go_no_go_multifile_case" / "input"

    summary, detail = load_multifile_case_dataset(dataset_dir)

    assert len(summary) >= 3
    assert len(detail) >= 8
    assert any(block.metadata.get("document_type") == "security" for block in detail)
    assert any(block.metadata.get("document_type") == "operations" for block in detail)


def test_load_multifile_case_dataset_raises_for_missing_dir(tmp_path: Path) -> None:
    missing_dir = tmp_path / "missing_multifile_case"

    try:
        _ = load_multifile_case_dataset(missing_dir)
    except FileNotFoundError as exc:
        assert "не найдена" in str(exc)
    else:
        raise AssertionError("Ожидалась ошибка отсутствующей директории")
