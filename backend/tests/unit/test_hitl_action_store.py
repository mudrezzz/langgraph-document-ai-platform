from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from application.hitl_action_store import (
    InMemoryHitlActionStore,
    HitlActionRecord,
    build_hitl_action_cursor,
    decode_hitl_action_cursor,
)
from application.errors import InvalidCursorError


def test_inmemory_hitl_action_store_filters_and_pagination() -> None:
    store = InMemoryHitlActionStore()
    now = datetime.now(timezone.utc)
    store.save_action(
        HitlActionRecord(
            action_id="a1",
            task_id="t1",
            iteration=1,
            decision="needs_changes",
            status="completed",
            reviewer="alice",
            metadata={"reviewer": "alice"},
            created_at=now - timedelta(minutes=3),
        )
    )
    store.save_action(
        HitlActionRecord(
            action_id="a2",
            task_id="t1",
            iteration=2,
            decision="approve",
            status="completed",
            reviewer="alice",
            metadata={"reviewer": "alice"},
            created_at=now - timedelta(minutes=2),
        )
    )
    store.save_action(
        HitlActionRecord(
            action_id="a3",
            task_id="t2",
            iteration=1,
            decision="approve",
            status="queued",
            reviewer="bob",
            metadata={"reviewer": "bob"},
            created_at=now - timedelta(minutes=1),
        )
    )

    page = store.list_actions(task_id="t1", reviewer="alice", limit=1)
    assert page.total_returned == 1
    assert page.items[0].action_id == "a2"
    assert page.next_cursor is not None
    assert page.has_more is True

    next_page = store.list_actions(task_id="t1", reviewer="alice", limit=10, cursor=page.next_cursor)
    assert next_page.total_returned == 1
    assert next_page.items[0].action_id == "a1"


def test_hitl_action_cursor_validation() -> None:
    cursor = build_hitl_action_cursor(
        HitlActionRecord(
            action_id="a1",
            task_id="t1",
            iteration=1,
            decision="approve",
            status="completed",
            created_at=datetime.now(timezone.utc),
        )
    )
    decoded = decode_hitl_action_cursor(cursor)
    assert decoded.action_id == "a1"

    with pytest.raises(InvalidCursorError):
        decode_hitl_action_cursor("invalid_cursor")


def test_inmemory_hitl_action_store_summary_aggregates() -> None:
    store = InMemoryHitlActionStore()
    now = datetime.now(timezone.utc)
    store.save_action(
        HitlActionRecord(
            action_id="a1",
            task_id="t1",
            iteration=1,
            decision="needs_changes",
            status="completed",
            reviewer="alice",
            created_at=now - timedelta(minutes=3),
        )
    )
    store.save_action(
        HitlActionRecord(
            action_id="a2",
            task_id="t1",
            iteration=2,
            decision="approve",
            status="completed",
            reviewer="alice",
            created_at=now - timedelta(minutes=2),
        )
    )
    store.save_action(
        HitlActionRecord(
            action_id="a3",
            task_id="t2",
            iteration=1,
            decision="reject",
            status="processing",
            reviewer="bob",
            created_at=now - timedelta(minutes=1),
        )
    )

    summary = store.summarize_actions()

    assert summary.total_actions == 3
    assert summary.unique_tasks == 2
    assert summary.pending_actions == 1
    assert summary.completed_actions == 2
    assert summary.approve_total == 1
    assert summary.needs_changes_total == 1
    assert summary.reject_total == 1
    assert summary.max_iteration == 2
    assert summary.avg_iteration is not None

    statuses = {item.status: item.total for item in summary.statuses}
    assert statuses["completed"] == 2
    assert statuses["processing"] == 1

    decisions = {item.decision: item.total for item in summary.decisions}
    assert decisions == {"approve": 1, "needs_changes": 1, "reject": 1}

    reviewers = {item.reviewer: item for item in summary.reviewers}
    assert reviewers["alice"].total == 2
    assert reviewers["alice"].approve_total == 1
    assert reviewers["alice"].needs_changes_total == 1
    assert reviewers["bob"].reject_total == 1
