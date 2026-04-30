from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# Allow running as a direct script: `python agent_examples/run_example.py ...`.
if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agent_examples.common.framework_client import FrameworkClient
from agent_examples.common.io_utils import print_json, write_json
from agent_examples.common.runtime import LocalApiRuntime
from agent_examples.patterns.authoring_first.agent import AuthoringFirstAgent
from agent_examples.patterns.authoring_first.config import AuthoringFirstConfig
from agent_examples.patterns.authoring_first.prompts import DEFAULT_QUERY as AUTHORING_QUERY
from agent_examples.patterns.hitl_gate.agent import HitlGateAgent
from agent_examples.patterns.hitl_gate.config import HitlGateConfig
from agent_examples.patterns.hitl_gate.prompts import DEFAULT_QUERY as HITL_QUERY
from agent_examples.patterns.retrieval_first.agent import RetrievalFirstAgent
from agent_examples.patterns.retrieval_first.config import RetrievalFirstConfig
from agent_examples.patterns.retrieval_first.prompts import DEFAULT_QUERY as RETRIEVAL_QUERY


PATTERN_CHOICES = ("retrieval_first", "authoring_first", "hitl_gate")


@dataclass(frozen=True)
class PatternDescriptor:
    pattern_id: str
    title: str
    default_query: str


PATTERN_INDEX = {
    "retrieval_first": PatternDescriptor(
        pattern_id="retrieval_first",
        title="Retrieval First Agent",
        default_query=RETRIEVAL_QUERY,
    ),
    "authoring_first": PatternDescriptor(
        pattern_id="authoring_first",
        title="Authoring First Agent",
        default_query=AUTHORING_QUERY,
    ),
    "hitl_gate": PatternDescriptor(
        pattern_id="hitl_gate",
        title="HITL Gate Agent",
        default_query=HITL_QUERY,
    ),
}


def parse_hitl_decisions(raw: str) -> list[str]:
    decisions = [item.strip() for item in raw.split(",") if item.strip()]
    allowed = {"approve", "needs_changes", "reject"}
    invalid = [item for item in decisions if item not in allowed]
    if invalid:
        raise ValueError(f"Invalid HITL decisions: {invalid}. Allowed: {sorted(allowed)}")
    return decisions


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run product-style Python agent examples.")
    parser.add_argument("--pattern", choices=PATTERN_CHOICES, required=True)
    parser.add_argument("--query", default="")
    parser.add_argument("--base-url", default="")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8210)
    parser.add_argument("--startup-timeout-sec", type=int, default=30)
    parser.add_argument("--no-local-api", action="store_true", help="Do not start local uvicorn runtime.")
    parser.add_argument("--hitl-decisions", default="needs_changes,approve")
    parser.add_argument("--output-json", default="")
    parser.add_argument("--dry-run", action="store_true")
    return parser


def run_pattern(pattern: str, *, client: FrameworkClient, query: str, hitl_decisions: list[str]) -> dict[str, Any]:
    if pattern == "retrieval_first":
        agent = RetrievalFirstAgent(client=client, config=RetrievalFirstConfig())
        return agent.run(query=query)
    if pattern == "authoring_first":
        agent = AuthoringFirstAgent(client=client, config=AuthoringFirstConfig())
        return agent.run(query=query)
    if pattern == "hitl_gate":
        agent = HitlGateAgent(client=client, config=HitlGateConfig())
        return agent.run(query=query, decisions=hitl_decisions)
    raise ValueError(f"Unsupported pattern: {pattern}")


def main() -> None:
    args = build_parser().parse_args()
    descriptor = PATTERN_INDEX[args.pattern]

    query = args.query.strip() or descriptor.default_query
    hitl_decisions = parse_hitl_decisions(args.hitl_decisions)

    if args.base_url.strip():
        base_url = args.base_url.strip().rstrip("/")
    else:
        base_url = f"http://{args.host}:{args.port}"

    payload: dict[str, Any] = {
        "pattern": args.pattern,
        "title": descriptor.title,
        "query": query,
        "base_url": base_url,
        "mode": "dry_run" if args.dry_run else "execute",
        "notes": [
            "Examples use only framework public HTTP API.",
            "Pattern code is located in agent_examples/patterns/<pattern>/agent.py.",
        ],
    }

    if args.dry_run:
        print_json(payload)
        return

    if args.no_local_api:
        client = FrameworkClient(base_url=base_url)
        result = run_pattern(args.pattern, client=client, query=query, hitl_decisions=hitl_decisions)
    else:
        with LocalApiRuntime(host=args.host, port=args.port, startup_timeout_sec=args.startup_timeout_sec):
            client = FrameworkClient(base_url=base_url)
            result = run_pattern(args.pattern, client=client, query=query, hitl_decisions=hitl_decisions)

    payload["result"] = result
    print_json(payload)

    if args.output_json.strip():
        output_path = write_json(Path(args.output_json), payload)
        print_json({"output_json_written": str(output_path)})


if __name__ == "__main__":
    main()
