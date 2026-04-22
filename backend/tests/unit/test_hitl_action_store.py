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
