#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path


_PENDING_APPROVAL_RE = re.compile(r"\b(PENDING|WAITING)\b", re.IGNORECASE)
_BLOCKER_RE = re.compile(
    r"(не\s+закрыт|не\s+завершен|no-go|блокер|critical|high finding)",
    re.IGNORECASE,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Собирает markdown-отчет о readiness на основе retrieval evidence",
    )
    parser.add_argument("--task-id", required=True)
    parser.add_argument("--query", required=True)
    parser.add_argument("--evidence-file", required=True)
    parser.add_argument("--status-file", required=True)
    parser.add_argument("--events-summary-file", required=True)
    parser.add_argument("--output-file", required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    evidence_payload = _read_json(args.evidence_file)
    status_payload = _read_json(args.status_file)
    events_summary_payload = _read_json(args.events_summary_file)

    selected_blocks = evidence_payload.get("evidence_pack", {}).get("selected_blocks", [])
    selected_sources = evidence_payload.get("evidence_pack", {}).get("selected_sources", [])

    blockers = _detect_blockers(selected_blocks)
    pending_approvals = _detect_pending_approvals(selected_blocks)

    decision = "NO-GO" if blockers or pending_approvals else "GO"
    rationale: list[str] = []
    if blockers:
        rationale.append("обнаружены блокирующие риски/незакрытые пункты readiness")
    if pending_approvals:
        rationale.append("есть approvals со статусом PENDING/WAITING")
    if not rationale:
        rationale.append("критичных блокеров по evidence не выявлено")

    report = _build_report(
        task_id=args.task_id,
        query=args.query,
        task_status=status_payload.get("status", "unknown"),
        decision=decision,
        rationale=rationale,
        blockers=blockers,
        pending_approvals=pending_approvals,
        selected_sources=selected_sources,
        transitions=events_summary_payload.get("transitions", []),
        total_events=events_summary_payload.get("total_events", 0),
        unique_tasks=events_summary_payload.get("unique_tasks", 0),
    )

    output_path = Path(args.output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report, encoding="utf-8")
    print(f"report_written: {output_path}")


def _read_json(path: str) -> dict:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON в {path} должен быть объектом")
    return payload


def _detect_blockers(blocks: list[dict]) -> list[str]:
    matches: list[str] = []
    for block in blocks:
        text = str(block.get("text", "")).strip()
        if not text:
            continue
        if _BLOCKER_RE.search(text):
            matches.append(text)
    return _unique(matches)


def _detect_pending_approvals(blocks: list[dict]) -> list[str]:
    matches: list[str] = []
    for block in blocks:
        text = str(block.get("text", "")).strip()
        if not text:
            continue
        if _PENDING_APPROVAL_RE.search(text):
            matches.append(text)
    return _unique(matches)


def _build_report(
    *,
    task_id: str,
    query: str,
    task_status: str,
    decision: str,
    rationale: list[str],
    blockers: list[str],
    pending_approvals: list[str],
    selected_sources: list[dict],
    transitions: list[dict],
    total_events: int,
    unique_tasks: int,
) -> str:
    now_utc = datetime.now(timezone.utc).isoformat()

    lines: list[str] = []
    lines.append("# Release Readiness Report")
    lines.append("")
    lines.append(f"- Generated at (UTC): `{now_utc}`")
    lines.append(f"- Task ID: `{task_id}`")
    lines.append(f"- Task status: `{task_status}`")
    lines.append(f"- Query: `{query}`")
    lines.append("")
    lines.append("## Decision")
    lines.append("")
    lines.append(f"**{decision}**")
    lines.append("")
    lines.append("### Rationale")
    lines.append("")
    for item in rationale:
        lines.append(f"- {item}")

    lines.append("")
    lines.append("## Blockers")
    lines.append("")
    if blockers:
        for item in blockers:
            lines.append(f"- {item}")
    else:
        lines.append("- Не обнаружены")

    lines.append("")
    lines.append("## Pending Approvals")
    lines.append("")
    if pending_approvals:
        for item in pending_approvals:
            lines.append(f"- {item}")
    else:
        lines.append("- Не обнаружены")

    lines.append("")
    lines.append("## Evidence Sources")
    lines.append("")
    if selected_sources:
        for src in selected_sources[:10]:
            lines.append(
                f"- doc_id=`{src.get('doc_id')}`, version=`{src.get('version')}`, block_id=`{src.get('block_id')}`"
            )
    else:
        lines.append("- Нет источников")

    lines.append("")
    lines.append("## Task Events Summary")
    lines.append("")
    lines.append(f"- total_events: `{total_events}`")
    lines.append(f"- unique_tasks: `{unique_tasks}`")
    lines.append("")
    lines.append("### Transitions")
    lines.append("")
    if transitions:
        for item in transitions:
            lines.append(
                "- "
                f"`{item.get('from_status')}` -> `{item.get('to_status')}`: "
                f"`{item.get('total')}`"
            )
    else:
        lines.append("- Нет переходов")

    lines.append("")
    lines.append("## Recommendation")
    lines.append("")
    if decision == "NO-GO":
        lines.append(
            "- Закрыть блокеры и получить обязательные approvals (`Security`, `SRE`, `Release Manager`), "
            "после чего повторно выполнить smoke/demo."
        )
    else:
        lines.append("- Можно выходить на релизное окно при сохранении текущих KPI и сигналов мониторинга.")

    lines.append("")
    return "\n".join(lines)


def _unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in values:
        if item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result


if __name__ == "__main__":
    main()
