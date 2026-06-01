from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from agent_examples.common.path_setup import ensure_backend_paths

ensure_backend_paths(repo_root=Path(__file__).resolve().parents[3])

from agent_examples.patterns.async_batch.agent import AsyncBatchAgent
from agent_examples.patterns.async_batch.config import AsyncBatchConfig
from agent_examples.patterns.async_batch.prompts import DEFAULT_QUERIES


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run in-process async batch demo agent.")
    parser.add_argument("--query", action="append", default=[])
    parser.add_argument("--queries-file", default="")
    parser.add_argument("--batch-size", type=int, default=2)
    parser.add_argument("--dataset-id", default="saa_release_readiness")
    parser.add_argument("--requester", default="agent-examples-async-batch")
    parser.add_argument("--fail-fast", action="store_true", help="Stop on first failed item.")
    return parser


def _load_queries_from_file(path: str) -> list[str]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(payload, list):
        return [str(item) for item in payload]
    if isinstance(payload, dict) and isinstance(payload.get("queries"), list):
        return [str(item) for item in payload["queries"]]
    raise ValueError("queries file must be JSON list or {'queries': [...]} object")


def main() -> None:
    args = build_parser().parse_args()
    queries: list[str] = []
    if args.queries_file.strip():
        queries.extend(_load_queries_from_file(args.queries_file.strip()))
    queries.extend(args.query)
    if not queries:
        queries = list(DEFAULT_QUERIES)

    agent = AsyncBatchAgent(
        config=AsyncBatchConfig(
            requester=args.requester,
            case_dataset_id=args.dataset_id,
            batch_size=args.batch_size,
            continue_on_error=not args.fail_fast,
        )
    )
    result = agent.run(queries=queries)
    print(json.dumps(result, ensure_ascii=False, indent=4))


if __name__ == "__main__":
    main()

