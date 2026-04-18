from __future__ import annotations

from application.task_service import InMemoryTaskRegistry, TaskRecord
from infra.postgres.task_registry import PostgresTaskRegistry


def test_inmemory_task_registry_updates_timestamps_on_save() -> None:
    registry = InMemoryTaskRegistry()

    initial = TaskRecord(
        task_id="task-1",
        task_type="retrieval_pack",
        status="running",
        current_node="start",
    )
    registry.save(initial)
    first = registry.get("task-1")

    updated = first.model_copy(
        update={
            "status": "completed",
            "current_node": "completed",
            "details": {"selected_block_count": 3},
        }
    )
    registry.save(updated)
    second = registry.get("task-1")

    assert second.created_at == first.created_at
    assert second.updated_at is not None
    assert first.updated_at is not None
    assert second.updated_at >= first.updated_at
    assert second.status == "completed"


def test_postgres_task_registry_fallback_returns_history_ordered_by_update_time() -> None:
    registry = PostgresTaskRegistry(dsn=None, use_fallback_if_unset=True)

    registry.save(
        TaskRecord(
            task_id="task-1",
            task_type="retrieval_pack",
            status="running",
            current_node="start",
        )
    )
    registry.save(
        TaskRecord(
            task_id="task-2",
            task_type="retrieval_pack",
            status="running",
            current_node="start",
        )
    )

    task_1 = registry.get("task-1")
    registry.save(task_1.model_copy(update={"status": "completed", "current_node": "completed"}))

    history = registry.list_tasks(limit=10, offset=0)

    assert len(history) == 2
    assert history[0].task_id == "task-1"
    assert history[1].task_id == "task-2"
