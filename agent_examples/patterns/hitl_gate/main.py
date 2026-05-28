from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from agent_examples.common.path_setup import ensure_backend_paths

ensure_backend_paths(repo_root=Path(__file__).resolve().parents[3])

from agent_examples.patterns.hitl_gate.agent import HitlGateAgent
from agent_examples.patterns.hitl_gate.config import HitlGateConfig
from agent_examples.patterns.hitl_gate.prompts import DEFAULT_QUERY


def parse_hitl_decisions(raw: str) -> list[str]:
    values = [item.strip() for item in raw.split(",") if item.strip()]
    allowed = {"approve", "needs_changes", "reject"}
    invalid = [item for item in values if item not in allowed]
    if invalid:
        raise ValueError(f"Invalid decisions: {invalid}. Allowed: {sorted(allowed)}")
    return values


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run in-process HITL gate demo agent.")
    parser.add_argument("--query", default=DEFAULT_QUERY)
    parser.add_argument("--dataset-id", default="saa_release_readiness")
    parser.add_argument("--requester", default="agent-examples-hitl")
    parser.add_argument("--workflow-mode", default="multi_step", choices=["single_pass", "multi_step"])
    parser.add_argument("--draft-strategy", default="deterministic", choices=["deterministic", "auto"])
    parser.add_argument("--artifact-title", default="Agent Examples: HITL Review")
    parser.add_argument("--artifact-format", default="markdown", choices=["markdown", "json"])
    parser.add_argument("--hitl-required", action="store_true", default=True)
    parser.add_argument("--hitl-decisions", default="needs_changes,approve")
    parser.add_argument("--hitl-max-iterations", type=int, default=3)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    agent = HitlGateAgent(
        config=HitlGateConfig(
            requester=args.requester,
            case_dataset_id=args.dataset_id,
            workflow_mode=args.workflow_mode,
            draft_strategy=args.draft_strategy,
            artifact_title=args.artifact_title,
            artifact_format=args.artifact_format,
            hitl_required=args.hitl_required,
            hitl_max_iterations=args.hitl_max_iterations,
        )
    )
    result = agent.run(query=args.query, decisions=parse_hitl_decisions(args.hitl_decisions))
    print(json.dumps(result, ensure_ascii=False, indent=4))


if __name__ == "__main__":
    main()
