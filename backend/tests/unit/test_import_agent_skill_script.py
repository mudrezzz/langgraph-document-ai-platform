from __future__ import annotations

from pathlib import Path

import pytest

from scripts import import_agent_skill


def test_resolve_source_url_from_repo_path() -> None:
    url = import_agent_skill.resolve_source_url(
        skill_url="",
        repo="acme/demo",
        path="skills/SKILL.md",
        ref="main",
    )
    assert url == "https://raw.githubusercontent.com/acme/demo/main/skills/SKILL.md"


def test_normalize_blob_url_to_raw_url() -> None:
    normalized = import_agent_skill.normalize_github_url(
        "https://github.com/acme/demo/blob/main/skills/AGENT.md"
    )
    assert normalized == "https://raw.githubusercontent.com/acme/demo/main/skills/AGENT.md"


def test_resolve_source_url_requires_exactly_one_source_mode() -> None:
    with pytest.raises(ValueError):
        import_agent_skill.resolve_source_url(
            skill_url="https://github.com/acme/demo/blob/main/skills/SKILL.md",
            repo="acme/demo",
            path="skills/SKILL.md",
            ref="main",
        )

    with pytest.raises(ValueError):
        import_agent_skill.resolve_source_url(skill_url="", repo="", path="", ref="main")


def test_resolve_source_url_rejects_non_markdown() -> None:
    with pytest.raises(ValueError):
        import_agent_skill.resolve_source_url(
            skill_url="",
            repo="acme/demo",
            path="skills/README.txt",
            ref="main",
        )


def test_import_skill_dry_run(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(import_agent_skill, "fetch_markdown", lambda **_: "# imported skill\n")

    payload = import_agent_skill.import_skill(
        agent="codex",
        skill_url="https://github.com/acme/demo/blob/main/skills/SKILL.md",
        repo="",
        path="",
        ref="main",
        target_root=str(tmp_path),
        target_filename="",
        max_bytes=1000,
        timeout_seconds=5,
        overwrite=False,
        dry_run=True,
    )

    assert payload["status"] == "dry_run"
    assert payload["agent"] == "codex"
    assert payload["source_url"] == "https://raw.githubusercontent.com/acme/demo/main/skills/SKILL.md"
    assert payload["target_path"].endswith(str(Path("codex") / "SKILL.md"))
    assert not (tmp_path / "codex" / "SKILL.md").exists()


def test_import_skill_writes_and_respects_overwrite(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(import_agent_skill, "fetch_markdown", lambda **_: "# v1\n")

    first = import_agent_skill.import_skill(
        agent="claude",
        skill_url="https://raw.githubusercontent.com/acme/demo/main/skills/agent.md",
        repo="",
        path="",
        ref="main",
        target_root=str(tmp_path),
        target_filename="",
        max_bytes=1000,
        timeout_seconds=5,
        overwrite=False,
        dry_run=False,
    )
    target_path = Path(first["target_path"])
    assert target_path.exists()
    assert target_path.read_text(encoding="utf-8") == "# v1\n"

    with pytest.raises(FileExistsError):
        import_agent_skill.import_skill(
            agent="claude",
            skill_url="https://raw.githubusercontent.com/acme/demo/main/skills/agent.md",
            repo="",
            path="",
            ref="main",
            target_root=str(tmp_path),
            target_filename="",
            max_bytes=1000,
            timeout_seconds=5,
            overwrite=False,
            dry_run=False,
        )

    monkeypatch.setattr(import_agent_skill, "fetch_markdown", lambda **_: "# v2\n")
    second = import_agent_skill.import_skill(
        agent="claude",
        skill_url="https://raw.githubusercontent.com/acme/demo/main/skills/agent.md",
        repo="",
        path="",
        ref="main",
        target_root=str(tmp_path),
        target_filename="",
        max_bytes=1000,
        timeout_seconds=5,
        overwrite=True,
        dry_run=False,
    )
    assert second["status"] == "imported"
    assert target_path.read_text(encoding="utf-8") == "# v2\n"
