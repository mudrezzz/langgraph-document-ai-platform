from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from urllib.request import urlopen


ALLOWED_HOSTS = {"github.com", "raw.githubusercontent.com"}
AGENT_PRESETS = {
    "codex": {"default_filename": "SKILL.md"},
    "claude": {"default_filename": "SKILL.md"},
    "cursor": {"default_filename": "AGENT.md"},
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Import skill/agent markdown from GitHub for codex/claude/cursor."
    )
    parser.add_argument("--agent", choices=sorted(AGENT_PRESETS.keys()), required=True)
    parser.add_argument("--skill-url", default="", help="GitHub or raw GitHub URL to .md file")
    parser.add_argument("--repo", default="", help="GitHub repository in owner/name format")
    parser.add_argument("--path", default="", help="Path to markdown file inside repository")
    parser.add_argument("--ref", default="main", help="Git ref (branch/tag/sha), default: main")
    parser.add_argument(
        "--target-root",
        default=".vibecoder/skills",
        help="Target root directory where imported skill will be saved",
    )
    parser.add_argument("--target-filename", default="", help="Optional output file name")
    parser.add_argument("--max-bytes", type=int, default=512_000, help="Max downloaded size in bytes")
    parser.add_argument("--timeout-seconds", type=int, default=20)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def resolve_source_url(*, skill_url: str, repo: str, path: str, ref: str) -> str:
    has_url = bool(skill_url.strip())
    has_repo_path = bool(repo.strip() and path.strip())

    if has_url == has_repo_path:
        raise ValueError("Provide either --skill-url OR (--repo and --path).")

    if has_url:
        return normalize_github_url(skill_url.strip())

    repo_value = repo.strip()
    if repo_value.count("/") != 1:
        raise ValueError("--repo must be in owner/name format.")
    owner, name = repo_value.split("/", 1)
    if not owner or not name:
        raise ValueError("--repo must be in owner/name format.")

    normalized_path = path.strip().lstrip("/")
    if not normalized_path.lower().endswith(".md"):
        raise ValueError("--path must point to a .md file.")
    return f"https://raw.githubusercontent.com/{owner}/{name}/{ref.strip()}/{normalized_path}"


def normalize_github_url(url: str) -> str:
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    if host not in ALLOWED_HOSTS:
        raise ValueError("Only github.com and raw.githubusercontent.com URLs are allowed.")

    if host == "github.com":
        parts = [segment for segment in parsed.path.split("/") if segment]
        if len(parts) >= 5 and parts[2] == "blob":
            owner = parts[0]
            repo = parts[1]
            ref = parts[3]
            file_path = "/".join(parts[4:])
            raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/{ref}/{file_path}"
            _validate_markdown_path(file_path)
            return raw_url
        _validate_markdown_path(parsed.path)
        return url

    _validate_markdown_path(parsed.path)
    return url


def _validate_markdown_path(path: str) -> None:
    if not path.lower().endswith(".md"):
        raise ValueError("Only markdown files (.md) are supported.")


def fetch_markdown(*, url: str, max_bytes: int, timeout_seconds: int) -> str:
    if max_bytes <= 0:
        raise ValueError("--max-bytes must be > 0.")
    with urlopen(url, timeout=timeout_seconds) as response:  # nosec - URL host is explicitly allowlisted.
        payload = response.read(max_bytes + 1)
    if len(payload) > max_bytes:
        raise ValueError(f"Downloaded file exceeds limit ({max_bytes} bytes).")
    return payload.decode("utf-8")


def build_target_path(*, target_root: str, agent: str, target_filename: str, source_url: str) -> Path:
    preset_filename = AGENT_PRESETS[agent]["default_filename"]
    file_name = target_filename.strip() or preset_filename
    if not file_name.lower().endswith(".md"):
        raise ValueError("--target-filename must end with .md")
    url_name = Path(urlparse(source_url).path).name
    if target_filename.strip() == "":
        file_name = url_name or preset_filename
    return Path(target_root).resolve() / agent / file_name


def import_skill(
    *,
    agent: str,
    skill_url: str,
    repo: str,
    path: str,
    ref: str,
    target_root: str,
    target_filename: str,
    max_bytes: int,
    timeout_seconds: int,
    overwrite: bool,
    dry_run: bool,
) -> dict[str, Any]:
    source_url = resolve_source_url(skill_url=skill_url, repo=repo, path=path, ref=ref)
    target_path = build_target_path(
        target_root=target_root, agent=agent, target_filename=target_filename, source_url=source_url
    )

    if target_path.exists() and not overwrite:
        raise FileExistsError(f"Target file already exists: {target_path}. Use --overwrite to replace it.")

    markdown = fetch_markdown(url=source_url, max_bytes=max_bytes, timeout_seconds=timeout_seconds)

    if dry_run:
        return {
            "status": "dry_run",
            "agent": agent,
            "source_url": source_url,
            "target_path": str(target_path),
            "bytes": len(markdown.encode("utf-8")),
        }

    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(markdown, encoding="utf-8")
    return {
        "status": "imported",
        "agent": agent,
        "source_url": source_url,
        "target_path": str(target_path),
        "bytes": len(markdown.encode("utf-8")),
    }


def main() -> None:
    args = parse_args()
    payload = import_skill(
        agent=args.agent,
        skill_url=args.skill_url,
        repo=args.repo,
        path=args.path,
        ref=args.ref,
        target_root=args.target_root,
        target_filename=args.target_filename,
        max_bytes=args.max_bytes,
        timeout_seconds=args.timeout_seconds,
        overwrite=args.overwrite,
        dry_run=args.dry_run,
    )
    print(json.dumps(payload, ensure_ascii=False, indent=4))


if __name__ == "__main__":
    main()
