from __future__ import annotations

from pathlib import Path

from domain_rag.retrieval.release_packet_dataset import build_release_packet_dataset


def test_build_release_packet_dataset_from_markdown_case_file() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    markdown_path = repo_root / "backend" / "examples" / "cases" / "release_go_no_go_case" / "input" / "release_packet.md"

    payload = build_release_packet_dataset(markdown_path=markdown_path, dataset_id="release_go_no_go")

    assert payload["dataset_id"] == "release_go_no_go"
    assert len(payload["summary_blocks"]) >= 2
    assert len(payload["detail_blocks"]) >= 8

    summary_sections = {item["metadata"]["section"] for item in payload["summary_blocks"]}
    assert "Release Decision" in summary_sections
    assert "Key Risks" in summary_sections

    detail_sections = {item["metadata"]["section"] for item in payload["detail_blocks"]}
    assert "Security" in detail_sections
    assert "Approvals" in detail_sections
    assert "Rollback Plan" in detail_sections


def test_build_release_packet_dataset_raises_for_missing_file(tmp_path: Path) -> None:
    missing_file = tmp_path / "missing_release_packet.md"

    try:
        _ = build_release_packet_dataset(markdown_path=missing_file)
    except FileNotFoundError as exc:
        assert "не найден" in str(exc)
    else:
        raise AssertionError("Ожидалась ошибка отсутствующего markdown файла")
