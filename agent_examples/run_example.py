from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# Allow running as a direct script: `python agent_examples/run_example.py ...`.
if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agent_examples.common.path_setup import ensure_backend_paths

ensure_backend_paths(repo_root=Path(__file__).resolve().parents[1])

from agent_examples.common.io_utils import print_json, write_json
from agent_examples.patterns.async_batch.agent import AsyncBatchAgent
from agent_examples.patterns.async_batch.config import AsyncBatchConfig
from agent_examples.patterns.async_batch.prompts import DEFAULT_QUERIES as ASYNC_BATCH_QUERIES
from agent_examples.patterns.authoring_first.agent import AuthoringFirstAgent
from agent_examples.patterns.authoring_first.config import AuthoringFirstConfig
from agent_examples.patterns.authoring_first.prompts import DEFAULT_QUERY as AUTHORING_QUERY
from agent_examples.patterns.hitl_gate.agent import HitlGateAgent
from agent_examples.patterns.hitl_gate.config import HitlGateConfig
from agent_examples.patterns.hitl_gate.prompts import DEFAULT_QUERY as HITL_QUERY
from agent_examples.patterns.mcp_tool_facade.agent import run_demo_tool_call
from agent_examples.patterns.mcp_tool_facade.prompts import DEFAULT_QUERY as MCP_FACADE_QUERY
from agent_examples.patterns.device_search.agent import DeviceSearchAgent
from agent_examples.patterns.device_search.config import DeviceSearchConfig
from agent_examples.patterns.device_search.prompts import DEFAULT_QUERY as DEVICE_SEARCH_QUERY
from agent_examples.patterns.retrieval_first.agent import RetrievalFirstAgent
from agent_examples.patterns.retrieval_first.config import RetrievalFirstConfig
from agent_examples.patterns.retrieval_first.prompts import DEFAULT_QUERY as RETRIEVAL_QUERY

PATTERN_CHOICES = ("retrieval_first", "authoring_first", "hitl_gate", "device_search", "async_batch", "mcp_tool_facade")


@dataclass(frozen=True)
class PatternDescriptor:
    pattern_id: str
    title: str
    default_query: str
    execution_model: str


PATTERN_INDEX = {
    "retrieval_first": PatternDescriptor(
        pattern_id="retrieval_first",
        title="Retrieval First Agent",
        default_query=RETRIEVAL_QUERY,
        execution_model="in_process_framework_workflow",
    ),
    "authoring_first": PatternDescriptor(
        pattern_id="authoring_first",
        title="Authoring First Agent",
        default_query=AUTHORING_QUERY,
        execution_model="in_process_framework_workflow",
    ),
    "hitl_gate": PatternDescriptor(
        pattern_id="hitl_gate",
        title="HITL Gate Agent",
        default_query=HITL_QUERY,
        execution_model="in_process_framework_workflow",
    ),
    "device_search": PatternDescriptor(
        pattern_id="device_search",
        title="Device Search Agent",
        default_query=DEVICE_SEARCH_QUERY,
        execution_model="in_process_framework_workflow",
    ),
    "async_batch": PatternDescriptor(
        pattern_id="async_batch",
        title="Async Batch Agent",
        default_query=ASYNC_BATCH_QUERIES[0],
        execution_model="in_process_framework_workflow",
    ),
    "mcp_tool_facade": PatternDescriptor(
        pattern_id="mcp_tool_facade",
        title="MCP Tool Facade Agent",
        default_query=MCP_FACADE_QUERY,
        execution_model="in_process_framework_workflow",
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
    parser.add_argument("--no-local-api", action="store_true", help="Do not start local uvicorn runtime for API-driven patterns.")
    parser.add_argument("--hitl-decisions", default="needs_changes,approve")
    parser.add_argument("--output-json", default="")
    parser.add_argument("--dry-run", action="store_true")
    return parser


def _run_in_process_retrieval(query: str) -> dict[str, Any]:
    agent = RetrievalFirstAgent(config=RetrievalFirstConfig())
    return agent.run(query=query)


def _run_in_process_authoring(query: str) -> dict[str, Any]:
    agent = AuthoringFirstAgent(config=AuthoringFirstConfig())
    return agent.run(query=query)


def _run_in_process_device_search(query: str) -> dict[str, Any]:
    agent = DeviceSearchAgent(config=DeviceSearchConfig())
    return agent.run(query=query, non_interactive=True)


def _run_in_process_hitl(query: str, hitl_decisions: list[str]) -> dict[str, Any]:
    agent = HitlGateAgent(config=HitlGateConfig())
    return agent.run(query=query, decisions=hitl_decisions)


def _run_in_process_async_batch(query: str, has_custom_query: bool) -> dict[str, Any]:
    agent = AsyncBatchAgent(config=AsyncBatchConfig())
    queries = [query] if has_custom_query else list(ASYNC_BATCH_QUERIES)
    return agent.run(queries=queries)


def _run_in_process_mcp_tool_facade(query: str) -> dict[str, Any]:
    return run_demo_tool_call(query=query)


def main() -> None:
    args = build_parser().parse_args()
    descriptor = PATTERN_INDEX[args.pattern]
    has_custom_query = bool(args.query.strip())

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
        "mode": "dry_run" if args.dry_run else "execute",
        "execution_model": descriptor.execution_model,
        "notes": [
            "Pattern code is located in agent_examples/patterns/<pattern>/.",
            "retrieval_first, authoring_first, hitl_gate, device_search, async_batch, and mcp_tool_facade are in-process patterns.",
        ],
    }

    if args.dry_run:
        print_json(payload)
        return

    if args.pattern == "retrieval_first":
        result = _run_in_process_retrieval(query=query)
    elif args.pattern == "authoring_first":
        result = _run_in_process_authoring(query=query)
    elif args.pattern == "device_search":
        result = _run_in_process_device_search(query=query)
    elif args.pattern == "async_batch":
        result = _run_in_process_async_batch(query=query, has_custom_query=has_custom_query)
    elif args.pattern == "mcp_tool_facade":
        result = _run_in_process_mcp_tool_facade(query=query)
    elif args.pattern == "hitl_gate":
        result = _run_in_process_hitl(query=query, hitl_decisions=hitl_decisions)
    else:
        raise ValueError(f"Unsupported pattern: {args.pattern}")

    payload["result"] = result
    print_json(payload)

    if args.output_json.strip():
        output_path = write_json(Path(args.output_json), payload)
        print_json({"output_json_written": str(output_path)})


if __name__ == "__main__":
    main()
