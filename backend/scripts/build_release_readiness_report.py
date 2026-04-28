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
    parser.add_argument("--indexing-status-file", default="")
    parser.add_argument("--output-file", required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    evidence_payload = _read_json(args.evidence_file)
    status_payload = _read_json(args.status_file)
    events_summary_payload = _read_json(args.events_summary_file)
    indexing_status_payload = _read_json(args.indexing_status_file) if args.indexing_status_file else None

    report = build_report_from_payloads(
        task_id=args.task_id,
        query=args.query,
        evidence_payload=evidence_payload,
        status_payload=status_payload,
        events_summary_payload=events_summary_payload,
        indexing_status_payload=indexing_status_payload,
    )

    output_path = Path(args.output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report, encoding="utf-8")
    print(f"report_written: {output_path}")


def build_report_from_payloads(
    *,
    task_id: str,
    query: str,
    evidence_payload: dict,
    status_payload: dict,
    events_summary_payload: dict,
    indexing_status_payload: dict | None = None,
) -> str:
    selected_blocks = evidence_payload.get("evidence_pack", {}).get("selected_blocks", [])
    selected_sources = evidence_payload.get("evidence_pack", {}).get("selected_sources", [])
    unresolved_gaps = evidence_payload.get("evidence_pack", {}).get("unresolved_gaps", [])
    confidence_notes = evidence_payload.get("evidence_pack", {}).get("confidence_notes", [])

    blockers = _detect_blockers(selected_blocks)
    pending_approvals = _detect_pending_approvals(selected_blocks)
    source_mappings = _build_source_mappings(selected_blocks=selected_blocks, selected_sources=selected_sources)

    decision = "NO-GO" if blockers or pending_approvals else "GO"
    rationale: list[str] = []
    if blockers:
        rationale.append("обнаружены блокирующие риски/незакрытые пункты readiness")
    if pending_approvals:
        rationale.append("есть approvals со статусом PENDING/WAITING")
    if not rationale:
        rationale.append("критичных блокеров по evidence не выявлено")

    return _build_report(
        task_id=task_id,
        query=query,
        task_status=status_payload.get("status", "unknown"),
        task_details=status_payload.get("details", {}),
        decision=decision,
        rationale=rationale,
        blockers=blockers,
        pending_approvals=pending_approvals,
        selected_sources=selected_sources,
        source_mappings=source_mappings,
        unresolved_gaps=unresolved_gaps,
        confidence_notes=confidence_notes,
        indexing_details=(indexing_status_payload or {}).get("details", {}),
        transitions=events_summary_payload.get("transitions", []),
        total_events=events_summary_payload.get("total_events", 0),
        unique_tasks=events_summary_payload.get("unique_tasks", 0),
    )


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
    task_details: dict,
    decision: str,
    rationale: list[str],
    blockers: list[str],
    pending_approvals: list[str],
    selected_sources: list[dict],
    source_mappings: list[dict],
    unresolved_gaps: list[str],
    confidence_notes: list[str],
    indexing_details: dict,
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
    if task_details:
        lines.append(f"- Knowledge source: `{task_details.get('knowledge_source', 'case_dataset')}`")
        lines.append(f"- Retrieval backend: `{task_details.get('retrieval_backend', 'in_memory')}`")
        lines.append(f"- Retrieval quality gate: `{task_details.get('quality_gate_status', 'unknown')}`")
        lines.append(f"- Confidence: `{task_details.get('confidence', 'unknown')}`")
        if task_details.get('execution_mode'):
            lines.append(f"- Execution mode: `{task_details.get('execution_mode')}`")
        if task_details.get('async_provider'):
            lines.append(f"- Async provider: `{task_details.get('async_provider')}`")
        if task_details.get('queue_name'):
            lines.append(f"- Queue name: `{task_details.get('queue_name')}`")
        if task_details.get('dispatch_id'):
            lines.append(f"- Dispatch ID: `{task_details.get('dispatch_id')}`")
        if task_details.get('correlation_id'):
            lines.append(f"- Correlation ID: `{task_details.get('correlation_id')}`")
        if task_details.get('queue_wait_ms') is not None:
            lines.append(f"- Queue wait ms: `{task_details.get('queue_wait_ms')}`")
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

    if indexing_details:
        lines.append("")
        lines.append("## Canonical Quality Summary")
        lines.append("")
        quality_summary = indexing_details.get("quality_summary", {})
        lines.append(f"- quality_gate_status: `{indexing_details.get('quality_gate_status', quality_summary.get('gate_status', 'unknown'))}`")
        lines.append(f"- documents_total: `{indexing_details.get('documents_total', quality_summary.get('documents_total', 0))}`")
        lines.append(f"- file_types: `{', '.join(indexing_details.get('file_types', []))}`")
        lines.append(f"- embeddings_indexed: `{indexing_details.get('embeddings_indexed', 0)}`")
        lines.append(f"- quality_flags_total: `{quality_summary.get('quality_flags_total', len(indexing_details.get('quality_flags', [])))}`")
        lines.append(f"- parser_families: `{', '.join(quality_summary.get('parser_families', []))}`")
        lines.append(f"- extraction_modes: `{', '.join(quality_summary.get('extraction_modes', []))}`")
        lines.append(f"- parser_issues_total: `{quality_summary.get('parser_issues_total', 0)}`")
        lines.append(f"- documents_with_tables: `{quality_summary.get('documents_with_tables', 0)}`")
        lines.append(f"- documents_needing_ocr: `{quality_summary.get('documents_needing_ocr', 0)}`")
        flags = indexing_details.get("quality_flags", []) or quality_summary.get("warning_flags", []) or []
        if flags:
            lines.append("")
            lines.append("### Quality Flags")
            lines.append("")
            for flag in flags:
                lines.append(f"- `{flag}`")

        parser_quality = indexing_details.get("parser_quality", {})
        if parser_quality:
            lines.append("")
            lines.append("### Parser Diagnostics")
            lines.append("")
            for doc_id, summary in sorted(parser_quality.items()):
                issues = summary.get("issues", [])
                lines.append(
                    "- "
                    f"doc_id=`{doc_id}`, "
                    f"parser_family=`{summary.get('parser_family', 'unknown')}`, "
                    f"blocks_total=`{summary.get('blocks_total', 0)}`, "
                    f"tables_total=`{summary.get('tables_total', 0)}`, "
                    f"issues_total=`{len(issues)}`"
                )

    lines.append("")
    lines.append("## Retrieval Quality")
    lines.append("")
    if confidence_notes:
        lines.append("### Confidence Notes")
        lines.append("")
        for note in confidence_notes:
            lines.append(f"- `{note}`")
    else:
        lines.append("- Confidence notes: none")

    lines.append("")
    lines.append("### Unresolved Gaps")
    lines.append("")
    if unresolved_gaps:
        for gap in unresolved_gaps:
            lines.append(f"- `{gap}`")
    else:
        lines.append("- Нет unresolved gaps")

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
    lines.append("## Canonical Source Mapping")
    lines.append("")
    if source_mappings:
        for item in source_mappings[:15]:
            quality = ", ".join(item.get("quality_flags", [])) or "none"
            provenance_bits: list[str] = []
            if item.get("table_title"):
                provenance_bits.append(f"table_title=`{item.get('table_title')}`")
            if item.get("table_row_refs"):
                provenance_bits.append(f"table_rows=`{', '.join(item.get('table_row_refs', []))}`")
            if item.get("page_refs"):
                provenance_bits.append(f"pages=`{', '.join(item.get('page_refs', []))}`")
            if item.get("layout_sources"):
                provenance_bits.append(f"layout_sources=`{', '.join(item.get('layout_sources', []))}`")
            if item.get("layout_kinds"):
                provenance_bits.append(f"layout_kinds=`{', '.join(item.get('layout_kinds', []))}`")
            provenance_suffix = f", {' , '.join(provenance_bits)}" if provenance_bits else ""
            lines.append(
                "- "
                f"doc_id=`{item.get('doc_id')}`, "
                f"file_type=`{item.get('file_type')}`, "
                f"source_path=`{item.get('source_path')}`, "
                f"evidence_blocks=`{item.get('evidence_blocks')}`, "
                f"quality_flags=`{quality}`{provenance_suffix}"
            )
    else:
        lines.append("- Нет canonical source mapping")

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


def _build_source_mappings(*, selected_blocks: list[dict], selected_sources: list[dict]) -> list[dict]:
    by_doc: dict[str, dict] = {}

    for source in selected_sources:
        doc_id = str(source.get("doc_id", "")).strip()
        if not doc_id:
            continue
        item = by_doc.setdefault(
            doc_id,
            {
                "doc_id": doc_id,
                "version": source.get("version"),
                "block_ids": set(),
                "evidence_blocks": 0,
                "quality_flags": [],
            },
        )
        block_id = source.get("block_id")
        if block_id:
            item["block_ids"].add(block_id)

    for block in selected_blocks:
        source = block.get("source", {}) or {}
        metadata = block.get("metadata", {}) or {}
        doc_id = str(source.get("doc_id", "")).strip()
        if not doc_id:
            continue
        item = by_doc.setdefault(
            doc_id,
            {
                "doc_id": doc_id,
                "version": source.get("version"),
                "block_ids": set(),
                "evidence_blocks": 0,
                "quality_flags": [],
            },
        )
        item["evidence_blocks"] += 1
        block_id = source.get("block_id")
        if block_id:
            item["block_ids"].add(block_id)
        for key in ("source_path", "file_type", "document_type", "doc_title"):
            if metadata.get(key) and not item.get(key):
                item[key] = metadata.get(key)
        if metadata.get("table_title") and not item.get("table_title"):
            item["table_title"] = metadata.get("table_title")
        if metadata.get("source_kind") == "table_row":
            row_index = metadata.get("row_index")
            row_ref = f"row_{row_index}" if row_index is not None else "row_unknown"
            item.setdefault("table_row_refs", [])
            if row_ref not in item["table_row_refs"]:
                item["table_row_refs"].append(row_ref)
        page_number = metadata.get("page_number")
        if isinstance(page_number, int):
            page_ref = f"p{page_number}"
            item.setdefault("page_refs", [])
            if page_ref not in item["page_refs"]:
                item["page_refs"].append(page_ref)
        layout_source = str(metadata.get("layout_source", "")).strip()
        if layout_source:
            item.setdefault("layout_sources", [])
            if layout_source not in item["layout_sources"]:
                item["layout_sources"].append(layout_source)
        layout_kind = str(metadata.get("layout_kind", "")).strip()
        if layout_kind:
            item.setdefault("layout_kinds", [])
            if layout_kind not in item["layout_kinds"]:
                item["layout_kinds"].append(layout_kind)
        for flag in metadata.get("quality_flags", []) or []:
            if flag not in item["quality_flags"]:
                item["quality_flags"].append(flag)

    result: list[dict] = []
    for item in by_doc.values():
        normalized = dict(item)
        normalized["block_ids"] = sorted(str(block_id) for block_id in item.get("block_ids", set()))
        normalized.setdefault("source_path", "")
        normalized.setdefault("file_type", "")
        normalized.setdefault("document_type", "")
        normalized.setdefault("doc_title", "")
        normalized.setdefault("table_title", "")
        normalized["table_row_refs"] = sorted(normalized.get("table_row_refs", []))
        normalized["page_refs"] = sorted(normalized.get("page_refs", []))
        normalized["layout_sources"] = sorted(normalized.get("layout_sources", []))
        normalized["layout_kinds"] = sorted(normalized.get("layout_kinds", []))
        result.append(normalized)

    result.sort(key=lambda item: (-int(item.get("evidence_blocks", 0)), item.get("doc_id", "")))
    return result


if __name__ == "__main__":
    main()
