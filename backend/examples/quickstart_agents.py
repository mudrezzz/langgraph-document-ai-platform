from __future__ import annotations

import argparse
import json
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


class ExampleNotFoundError(KeyError):
    """Raised when an unknown example id is requested."""


@dataclass(frozen=True)
class ExampleSpec:
    """Minimal contract for a runnable framework example."""

    example_id: str
    title: str
    pattern: str
    summary: str
    script_stem: str
    default_args: tuple[str, ...]
    prerequisites: tuple[str, ...]

    def script_path(self, repo_root: Path, *, platform_hint: str) -> Path:
        suffix = ".ps1" if platform_hint == "windows" else ".sh"
        return repo_root / "backend" / "scripts" / f"{self.script_stem}{suffix}"


EXAMPLE_REGISTRY: dict[str, ExampleSpec] = {
    "retrieval_faq_assistant": ExampleSpec(
        example_id="retrieval_faq_assistant",
        title="Retrieval FAQ Assistant",
        pattern="Retrieval-First Agent",
        summary="Запускает retrieval smoke path и возвращает evidence pack по query.",
        script_stem="smoke_retrieval_api",
        default_args=("--port", "8110", "--query", "release readiness faq evidence"),
        prerequisites=(
            "bash backend/scripts/postgres_up.sh",
            "bash backend/scripts/postgres_migrate.sh",
        ),
    ),
    "authoring_policy_brief": ExampleSpec(
        example_id="authoring_policy_brief",
        title="Authoring Policy Brief",
        pattern="Authoring-First Agent",
        summary="Запускает authoring flow и строит artifact с traceability.",
        script_stem="smoke_authoring_api",
        default_args=(
            "--port",
            "8130",
            "--workflow-mode",
            "multi_step",
            "--draft-strategy",
            "deterministic",
        ),
        prerequisites=(
            "bash backend/scripts/postgres_up.sh",
            "bash backend/scripts/postgres_migrate.sh",
        ),
    ),
    "hitl_review_loop": ExampleSpec(
        example_id="hitl_review_loop",
        title="HITL Review Loop",
        pattern="HITL Gate Pattern",
        summary="Запускает async authoring с итеративным reviewer loop needs_changes -> approve.",
        script_stem="smoke_authoring_async_api",
        default_args=(
            "--port",
            "8150",
            "--hitl-required",
            "--hitl-decision-sequence",
            "needs_changes,approve",
            "--workflow-mode",
            "multi_step",
        ),
        prerequisites=(
            "bash backend/scripts/postgres_up.sh",
            "bash backend/scripts/postgres_migrate.sh",
            "bash backend/scripts/async_up.sh",
        ),
    ),
}


def _normalize_platform(platform_hint: str | None) -> str:
    if platform_hint in {"linux", "windows"}:
        return platform_hint
    return "windows" if os.name == "nt" else "linux"


def list_examples() -> list[dict[str, object]]:
    return [
        {
            "example_id": spec.example_id,
            "title": spec.title,
            "pattern": spec.pattern,
            "summary": spec.summary,
            "prerequisites": list(spec.prerequisites),
        }
        for spec in EXAMPLE_REGISTRY.values()
    ]


def get_example_spec(example_id: str) -> ExampleSpec:
    spec = EXAMPLE_REGISTRY.get(example_id)
    if spec is None:
        raise ExampleNotFoundError(f"Unknown example id: {example_id}")
    return spec


def build_example_command(
    example_id: str,
    *,
    platform_hint: str | None = None,
    extra_args: Iterable[str] = (),
) -> list[str]:
    spec = get_example_spec(example_id)
    normalized_platform = _normalize_platform(platform_hint)
    repo_root = Path(__file__).resolve().parents[2]
    script_path = spec.script_path(repo_root, platform_hint=normalized_platform)
    if not script_path.exists():
        raise FileNotFoundError(f"Example script not found: {script_path}")

    if normalized_platform == "windows":
        command: list[str] = ["pwsh", "-File", str(script_path)]
    else:
        command = ["bash", str(script_path)]

    command.extend(spec.default_args)
    command.extend(list(extra_args))
    return command


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run framework examples for quick developer onboarding.")
    parser.add_argument("--list", action="store_true", help="Show available examples and exit.")
    parser.add_argument("--example", default="", help="Example id from --list output.")
    parser.add_argument("--platform", choices=["linux", "windows"], default=None)
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Execute the example command. Default mode is dry-run (print command only).",
    )
    parser.add_argument(
        "--extra-arg",
        action="append",
        default=[],
        help="Extra argument forwarded to underlying smoke script. Repeat flag to pass multiple args.",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()

    if args.list:
        print(json.dumps({"examples": list_examples()}, ensure_ascii=False, indent=4))
        return

    if not args.example.strip():
        raise SystemExit("Pass --example <id> or use --list.")

    spec = get_example_spec(args.example.strip())
    command = build_example_command(spec.example_id, platform_hint=args.platform, extra_args=args.extra_arg)

    payload = {
        "example_id": spec.example_id,
        "title": spec.title,
        "pattern": spec.pattern,
        "summary": spec.summary,
        "prerequisites": list(spec.prerequisites),
        "command": command,
        "mode": "execute" if args.execute else "dry-run",
    }
    print(json.dumps(payload, ensure_ascii=False, indent=4))

    if not args.execute:
        return

    result = subprocess.run(command, check=False)
    if result.returncode != 0:
        raise SystemExit(result.returncode)


if __name__ == "__main__":
    main()
