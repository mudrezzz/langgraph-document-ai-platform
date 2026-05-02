"""Entry point for the device search agent.

Usage:
  .venv/bin/python agent_examples/patterns/device_search/main.py
  .venv/bin/python agent_examples/patterns/device_search/main.py \\
      --query "ноутбук для ml разработки бюджет 120000"

Requires:
  OPENROUTER_API_KEY env var (free tier is sufficient)
  OPENROUTER_MODEL  env var (default: openai/gpt-4o-mini)
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from agent_examples.common.path_setup import ensure_backend_paths

ensure_backend_paths(repo_root=Path(__file__).resolve().parents[3])

from agent_examples.patterns.device_search.agent import DeviceSearchAgent
from agent_examples.patterns.device_search.config import DeviceSearchConfig
from agent_examples.patterns.device_search.prompts import DEFAULT_QUERY


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Device search agent — find and compare devices with evidence-backed scoring."
    )
    parser.add_argument("--query", default=DEFAULT_QUERY, help="User query in natural language")
    parser.add_argument(
        "--non-interactive",
        action="store_true",
        help="Skip HITL stdin prompt (auto-approve criteria)",
    )
    parser.add_argument(
        "--report-only",
        action="store_true",
        help="Print only the final Markdown report, not the full JSON result",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    config = DeviceSearchConfig()

    if not config.openrouter_api_key:
        print(
            "ERROR: OPENROUTER_API_KEY is not set.\n"
            "Export it: export OPENROUTER_API_KEY=sk-or-...",
            file=sys.stderr,
        )
        sys.exit(1)

    print(f"\n[device-search] Запрос: «{args.query}»")
    print(f"[device-search] Модель: {config.openrouter_model}")

    agent = DeviceSearchAgent(config=config)
    result = agent.run(query=args.query, non_interactive=args.non_interactive)

    if args.report_only:
        print("\n" + "=" * 70)
        print(result.get("final_report") or "(отчёт не сформирован)")
    else:
        # Print report prominently, then the machine-readable JSON
        report = result.pop("final_report", None)
        print("\n" + "=" * 70)
        print("ИТОГОВЫЙ ОТЧЁТ")
        print("=" * 70)
        print(report or "(отчёт не сформирован)")
        print("\n" + "=" * 70)
        print("СТРУКТУРИРОВАННЫЙ РЕЗУЛЬТАТ (JSON)")
        print("=" * 70)
        result["final_report"] = report
        print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
