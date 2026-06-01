from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from agent_examples.common.path_setup import ensure_backend_paths

ensure_backend_paths(repo_root=Path(__file__).resolve().parents[3])

from agent_examples.patterns.mcp_tool_facade.agent import run_demo_tool_call
from agent_examples.patterns.mcp_tool_facade.prompts import DEFAULT_QUERY


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run in-process MCP tool facade demo agent.")
    parser.add_argument("--query", default=DEFAULT_QUERY)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    payload = run_demo_tool_call(query=args.query)
    print(json.dumps(payload, ensure_ascii=False, indent=4))


if __name__ == "__main__":
    main()

