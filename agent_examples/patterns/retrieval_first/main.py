from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from agent_examples.common.path_setup import ensure_backend_paths

ensure_backend_paths(repo_root=Path(__file__).resolve().parents[3])

from agent_examples.patterns.retrieval_first.agent import RetrievalFirstAgent
from agent_examples.patterns.retrieval_first.config import RetrievalFirstConfig
from agent_examples.patterns.retrieval_first.prompts import DEFAULT_QUERY


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run in-process retrieval-first demo agent.")
    parser.add_argument("--query", default=DEFAULT_QUERY)
    parser.add_argument("--dataset-id", default="saa_release_readiness")
    parser.add_argument("--requester", default="agent-examples-retrieval")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    agent = RetrievalFirstAgent(
        config=RetrievalFirstConfig(
            requester=args.requester,
            case_dataset_id=args.dataset_id,
        )
    )
    result = agent.run(query=args.query)
    print(json.dumps(result, ensure_ascii=False, indent=4))


if __name__ == "__main__":
    main()
