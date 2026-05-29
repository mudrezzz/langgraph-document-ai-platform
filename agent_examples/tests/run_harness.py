from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Unified test harness for agent_examples.")
    parser.add_argument("--lane", choices=["fast", "full"], default="fast")
    parser.add_argument(
        "--run-external-llm-smoke",
        action="store_true",
        help="Run device_search smoke even if RUN_EXTERNAL_LLM_TESTS is not set.",
    )
    parser.add_argument(
        "--require-external-llm-smoke",
        action="store_true",
        help="Fail full lane if device_search smoke was not executed.",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    run_fast_lane()

    if args.lane == "full":
        ran_external = run_external_llm_smoke(force=args.run_external_llm_smoke)
        if args.require_external_llm_smoke and not ran_external:
            raise SystemExit(
                "Full lane requires external LLM smoke, but it was skipped. "
                "Set RUN_EXTERNAL_LLM_TESTS=1 and OPENROUTER_API_KEY, or pass --run-external-llm-smoke."
            )


def run_fast_lane() -> None:
    commands = [
        [sys.executable, "-m", "pytest", "-q", "agent_examples/patterns/retrieval_first/tests/test_agent.py"],
        [sys.executable, "-m", "pytest", "-q", "agent_examples/patterns/authoring_first/tests/test_agent.py"],
        [sys.executable, "-m", "pytest", "-q", "agent_examples/patterns/hitl_gate/tests/test_agent.py"],
        [sys.executable, "-m", "pytest", "-q", "agent_examples/tests/test_run_example.py"],
        [sys.executable, "-m", "pytest", "-q", "backend/tests/unit/test_agent_examples_contracts.py"],
    ]
    for command in commands:
        run_command(command, label="fast")


def run_external_llm_smoke(*, force: bool) -> bool:
    enabled_by_env = os.getenv("RUN_EXTERNAL_LLM_TESTS", "0").strip() == "1"
    has_key = bool(os.getenv("OPENROUTER_API_KEY", "").strip())

    if not force and not (enabled_by_env and has_key):
        print(
            "[full] Skipping device_search smoke: set RUN_EXTERNAL_LLM_TESTS=1 and OPENROUTER_API_KEY "
            "or pass --run-external-llm-smoke."
        )
        return False

    command = [
        sys.executable,
        "agent_examples/run_example.py",
        "--pattern",
        "device_search",
    ]
    run_command(command, label="full")
    return True


def run_command(command: list[str], *, label: str) -> None:
    print(f"[{label}] $ {' '.join(command)}")
    subprocess.run(command, cwd=str(REPO_ROOT), check=True)


if __name__ == "__main__":
    main()
