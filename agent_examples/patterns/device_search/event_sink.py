"""WorkflowNodeEventSink implementation for the device search agent.

Collects node-level events across all three workflow phases (planning /
research / report) and exposes a unified timeline with per-node timing.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from framework.workflows.base import WorkflowNodeEventRecord


@dataclass
class _NodeEntry:
    workflow_name: str
    node_name: str
    status: str  # started | completed | failed
    timestamp: float
    duration_ms: int | None = None
    error: str | None = None


class DeviceSearchEventSink:
    """In-memory WorkflowNodeEventSink with real-time console output.

    Pass one shared instance to all three workflow phases so every node
    appears in a single unified timeline.

    Usage::

        sink = DeviceSearchEventSink()
        planning_wf = DevicePlanningWorkflow(llm=llm, event_sink=sink)
        research_wf = DeviceResearchWorkflow(llm=llm, event_sink=sink)
        report_wf   = DeviceReportWorkflow(llm=llm, event_sink=sink)
        ...
        sink.print_timeline()
        events = sink.get_timeline()
    """

    def __init__(self, verbose: bool = True) -> None:
        self._verbose = verbose
        self._entries: list[_NodeEntry] = []
        self._start_times: dict[str, float] = {}

    # ── WorkflowNodeEventSink protocol ───────────────────────────────────────

    def record_node_event(self, event: WorkflowNodeEventRecord) -> None:
        ts = time.time()

        if event.status == "started":
            self._start_times[event.node_name] = ts
            self._entries.append(_NodeEntry(
                workflow_name=event.workflow_name,
                node_name=event.node_name,
                status="started",
                timestamp=ts,
            ))
            if self._verbose:
                print(f"    ▶ {event.node_name}", flush=True)

        elif event.status == "completed":
            started = self._start_times.get(event.node_name, ts)
            duration_ms = int((ts - started) * 1000)
            self._entries.append(_NodeEntry(
                workflow_name=event.workflow_name,
                node_name=event.node_name,
                status="completed",
                timestamp=ts,
                duration_ms=duration_ms,
            ))
            if self._verbose:
                print(f"    ✓ {event.node_name}  {duration_ms}ms", flush=True)

        elif event.status == "failed":
            started = self._start_times.get(event.node_name, ts)
            duration_ms = int((ts - started) * 1000)
            self._entries.append(_NodeEntry(
                workflow_name=event.workflow_name,
                node_name=event.node_name,
                status="failed",
                timestamp=ts,
                duration_ms=duration_ms,
                error=event.error,
            ))
            if self._verbose:
                print(
                    f"    ✗ {event.node_name}  {duration_ms}ms  ERROR: {event.error}",
                    flush=True,
                )

    # ── Public API ────────────────────────────────────────────────────────────

    def get_timeline(self) -> list[dict[str, Any]]:
        """Return all node events as plain dicts for JSON serialisation."""
        return [
            {
                "workflow": e.workflow_name,
                "node": e.node_name,
                "status": e.status,
                "timestamp": round(e.timestamp, 3),
                **({"duration_ms": e.duration_ms} if e.duration_ms is not None else {}),
                **({"error": e.error} if e.error else {}),
            }
            for e in self._entries
        ]

    def get_completed_nodes(self) -> list[dict[str, Any]]:
        """Return only completed-node entries with timing, sorted by execution order."""
        return [
            {"node": e.node_name, "workflow": e.workflow_name, "duration_ms": e.duration_ms}
            for e in self._entries
            if e.status == "completed"
        ]

    def get_failed_nodes(self) -> list[dict[str, Any]]:
        return [
            {"node": e.node_name, "error": e.error, "duration_ms": e.duration_ms}
            for e in self._entries
            if e.status == "failed"
        ]

    def total_duration_ms(self) -> int:
        completed = [e for e in self._entries if e.duration_ms is not None]
        return sum(e.duration_ms for e in completed)  # type: ignore[misc]

    def print_timeline(self) -> None:
        """Print a formatted node execution timeline to stdout."""
        print("\n" + "=" * 62)
        print("NODE EXECUTION TIMELINE")
        print("=" * 62)
        completed = self.get_completed_nodes()
        for entry in completed:
            print(
                f"  {'✓':1s}  {entry['node']:<32s}  {entry['duration_ms']:>5}ms"
                f"  [{entry['workflow']}]"
            )
        failed = self.get_failed_nodes()
        for entry in failed:
            print(f"  {'✗':1s}  {entry['node']:<32s}  ERROR: {entry['error']}")

        total = self.total_duration_ms()
        print("-" * 62)
        print(f"  Total wall time (node execution): {total}ms")
        print("=" * 62)
