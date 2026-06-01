from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from agent_examples.common.path_setup import ensure_backend_paths

ensure_backend_paths(repo_root=Path(__file__).resolve().parents[3])

from agent_examples.patterns.authoring_first.agent import AuthoringFirstAgent
from agent_examples.patterns.authoring_first.config import AuthoringFirstConfig
from agent_examples.patterns.authoring_first.prompts import DEFAULT_QUERY


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run in-process authoring-first demo agent.")
    parser.add_argument("--query", default=DEFAULT_QUERY)
    parser.add_argument("--dataset-id", default="saa_release_readiness")
    parser.add_argument("--requester", default="agent-examples-authoring")
    parser.add_argument("--workflow-mode", default="multi_step", choices=["single_pass", "multi_step"])
    parser.add_argument("--draft-strategy", default="deterministic", choices=["deterministic", "auto"])
    parser.add_argument("--artifact-title", default="Agent Examples: Policy Brief")
    parser.add_argument("--artifact-format", default="markdown", choices=["markdown", "json"])
    return parser


def main() -> None:
    args = build_parser().parse_args()
    agent = AuthoringFirstAgent(
        config=AuthoringFirstConfig(
            requester=args.requester,
            case_dataset_id=args.dataset_id,
            workflow_mode=args.workflow_mode,
            draft_strategy=args.draft_strategy,
            artifact_title=args.artifact_title,
            artifact_format=args.artifact_format,
        )
    )
    result = agent.run(query=args.query)
    print(json.dumps(result, ensure_ascii=False, indent=4))


if __name__ == "__main__":
    main()
