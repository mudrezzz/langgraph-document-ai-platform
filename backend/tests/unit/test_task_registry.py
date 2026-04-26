from __future__ import annotations

from datetime import datetime, timedelta, timezone

from application.task_service import InMemoryTaskRegistry, TaskApplicationService, TaskEventRecord, TaskRecord
from framework.workflows.base import WorkflowNodeEventRecord
from infra.postgres.checkpoint_store import LangGraphPostgresCheckpointStore
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


def test_postgres_task_registry_fallback_cursor_pagination() -> None:
    registry = PostgresTaskRegistry(dsn=None, use_fallback_if_unset=True)
    base = datetime(2026, 4, 19, 10, 0, tzinfo=timezone.utc)

    registry.save(
        TaskRecord(
            task_id="task-c",
            task_type="retrieval_pack",
            status="completed",
            current_node="completed",
            created_at=base + timedelta(seconds=1),
            updated_at=base + timedelta(seconds=1),
        )
    )
    registry.save(
        TaskRecord(
            task_id="task-b",
            task_type="retrieval_pack",
            status="completed",
            current_node="completed",
            created_at=base + timedelta(seconds=2),
            updated_at=base + timedelta(seconds=2),
        )
    )
    registry.save(
        TaskRecord(
            task_id="task-a",
            task_type="retrieval_pack",
            status="completed",
            current_node="completed",
            created_at=base + timedelta(seconds=3),
            updated_at=base + timedelta(seconds=3),
        )
    )

    first_page = registry.list_tasks(limit=2)
    assert first_page.total_returned == 2
    assert first_page.has_more is True
    assert first_page.next_cursor is not None
    assert [item.task_id for item in first_page.items] == ["task-a", "task-b"]

    second_page = registry.list_tasks(limit=2, cursor=first_page.next_cursor)
    assert second_page.total_returned == 1
    assert second_page.has_more is False
    assert second_page.next_cursor is None
    assert [item.task_id for item in second_page.items] == ["task-c"]


def test_postgres_task_registry_fallback_applies_filters() -> None:
    registry = PostgresTaskRegistry(dsn=None, use_fallback_if_unset=True)
    base = datetime(2026, 4, 19, 12, 0, tzinfo=timezone.utc)

    registry.save(
        TaskRecord(
            task_id="task-1",
            task_type="retrieval_pack",
            status="completed",
            current_node="completed",
            created_at=base,
            updated_at=base,
        )
    )
    registry.save(
        TaskRecord(
            task_id="task-2",
            task_type="retrieval_pack",
            status="failed",
            current_node="failed",
            created_at=base + timedelta(minutes=5),
            updated_at=base + timedelta(minutes=5),
        )
    )
    registry.save(
        TaskRecord(
            task_id="task-3",
            task_type="indexing_pack",
            status="completed",
            current_node="completed",
            created_at=base + timedelta(minutes=10),
            updated_at=base + timedelta(minutes=10),
        )
    )

    completed_page = registry.list_tasks(limit=10, status="completed")
    assert {item.task_id for item in completed_page.items} == {"task-1", "task-3"}

    retrieval_only = registry.list_tasks(limit=10, task_type="retrieval_pack")
    assert {item.task_id for item in retrieval_only.items} == {"task-1", "task-2"}

    ranged = registry.list_tasks(
        limit=10,
        updated_from=base + timedelta(minutes=4),
        updated_to=base + timedelta(minutes=6),
    )
    assert [item.task_id for item in ranged.items] == ["task-2"]


def test_postgres_task_registry_fallback_records_status_audit_events() -> None:
    registry = PostgresTaskRegistry(dsn=None, use_fallback_if_unset=True)

    registry.save(
        TaskRecord(
            task_id="task-1",
            task_type="retrieval_pack",
            status="running",
            current_node="start",
        )
    )
    first = registry.get("task-1")

    # При обновлении details без смены статуса новое событие не пишется.
    registry.save(first.model_copy(update={"details": {"step": "mid"}}))

    registry.save(
        first.model_copy(
            update={
                "status": "completed",
                "current_node": "completed",
                "details": {"step": "done"},
            }
        )
    )

    page = registry.list_task_events(task_id="task-1", limit=10)

    assert page.total_returned == 2
    assert page.has_more is False
    assert page.next_cursor is None
    assert page.items[0].from_status == "running"
    assert page.items[0].to_status == "completed"
    assert page.items[1].from_status is None
    assert page.items[1].to_status == "running"


def test_postgres_task_registry_fallback_records_explicit_node_events() -> None:
    registry = PostgresTaskRegistry(dsn=None, use_fallback_if_unset=True)
    registry.save(
        TaskRecord(
            task_id="task-1",
            task_type="retrieval_pack",
            status="running",
            current_node="start",
        )
    )

    registry.record_event(
        TaskEventRecord(
            task_id="task-1",
            task_type="retrieval_pack",
            from_status="running",
            to_status="running",
            from_current_node="start",
            to_current_node="invoke_entry",
            event_payload={
                "event_kind": "workflow_node",
                "workflow_name": "RetrievalPackWorkflow",
                "node_name": "invoke_entry",
                "node_status": "completed",
            },
        )
    )

    page = registry.list_task_events(task_id="task-1", to_status="running", limit=10)
    node_events = [item for item in page.items if item.event_payload.get("event_kind") == "workflow_node"]

    assert len(node_events) == 1
    assert node_events[0].from_status == "running"
    assert node_events[0].to_status == "running"
    assert node_events[0].to_current_node == "invoke_entry"
    assert node_events[0].event_payload["node_status"] == "completed"


def test_task_service_maps_workflow_node_events_to_task_events() -> None:
    registry = PostgresTaskRegistry(dsn=None, use_fallback_if_unset=True)
    service = TaskApplicationService(
        registry=registry,
        checkpoint_store=LangGraphPostgresCheckpointStore(dsn=None, use_fallback_if_unset=True),
    )
    task = service.create_task("retrieval_pack")
    sink = service.build_workflow_node_event_sink()

    sink.record_node_event(
        event=WorkflowNodeEventRecord(
            workflow_name="RetrievalPackWorkflow",
            node_name="invoke_entry",
            task_id=task.task_id,
            correlation_id="corr-1",
            status="started",
            metadata={"task_id": task.task_id, "correlation_id": "corr-1"},
        )
    )

    events = service.list_task_events(task_id=task.task_id, limit=10).items
    node_events = [item for item in events if item.event_payload.get("event_kind") == "workflow_node"]

    assert len(node_events) == 1
    assert node_events[0].event_payload["workflow_name"] == "RetrievalPackWorkflow"
    assert node_events[0].event_payload["node_name"] == "invoke_entry"
    assert node_events[0].event_payload["node_status"] == "started"
    assert node_events[0].event_payload["correlation_id"] == "corr-1"


def test_postgres_task_registry_fallback_task_events_cursor_and_filters() -> None:
    registry = PostgresTaskRegistry(dsn=None, use_fallback_if_unset=True)
    base = datetime(2026, 4, 19, 13, 0, tzinfo=timezone.utc)

    registry.save(
        TaskRecord(
            task_id="task-1",
            task_type="retrieval_pack",
            status="running",
            current_node="start",
            created_at=base,
            updated_at=base,
        )
    )
    registry.save(
        TaskRecord(
            task_id="task-1",
            task_type="retrieval_pack",
            status="completed",
            current_node="completed",
            created_at=base + timedelta(minutes=1),
            updated_at=base + timedelta(minutes=1),
        )
    )
    registry.save(
        TaskRecord(
            task_id="task-2",
            task_type="indexing_pack",
            status="running",
            current_node="start",
            created_at=base + timedelta(minutes=2),
            updated_at=base + timedelta(minutes=2),
        )
    )

    first_page = registry.list_task_events(limit=1)
    assert first_page.total_returned == 1
    assert first_page.has_more is True
    assert first_page.next_cursor is not None

    second_page = registry.list_task_events(limit=10, cursor=first_page.next_cursor)
    assert second_page.total_returned >= 1

    task_filtered = registry.list_task_events(limit=10, task_id="task-1")
    assert {item.task_id for item in task_filtered.items} == {"task-1"}

    type_filtered = registry.list_task_events(limit=10, task_type="indexing_pack")
    assert {item.task_id for item in type_filtered.items} == {"task-2"}

    transition_filtered = registry.list_task_events(limit=10, from_status="running", to_status="completed")
    assert len(transition_filtered.items) == 1
    assert transition_filtered.items[0].task_id == "task-1"
    assert transition_filtered.items[0].from_status == "running"
    assert transition_filtered.items[0].to_status == "completed"

    now_utc = datetime.now(timezone.utc)
    ranged = registry.list_task_events(
        limit=10,
        created_from=now_utc - timedelta(minutes=5),
        created_to=now_utc + timedelta(minutes=5),
    )
    assert len(ranged.items) >= 1


def test_postgres_task_registry_fallback_task_events_summary() -> None:
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
            task_id="task-1",
            task_type="retrieval_pack",
            status="completed",
            current_node="completed",
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

    summary = registry.summarize_task_events(task_type="retrieval_pack")

    assert summary.total_events == 3
    assert summary.unique_tasks == 2
    transitions = {(item.from_status, item.to_status): item.total for item in summary.transitions}
    assert transitions[(None, "running")] == 2
    assert transitions[("running", "completed")] == 1


def test_postgres_task_registry_fallback_task_events_summary_counts_queued_running_completed() -> None:
    registry = PostgresTaskRegistry(dsn=None, use_fallback_if_unset=True)

    registry.save(
        TaskRecord(
            task_id="task-queued",
            task_type="retrieval_pack",
            status="queued",
            current_node="queued",
        )
    )
    registry.save(
        TaskRecord(
            task_id="task-queued",
            task_type="retrieval_pack",
            status="running",
            current_node="start",
        )
    )
    registry.save(
        TaskRecord(
            task_id="task-queued",
            task_type="retrieval_pack",
            status="completed",
            current_node="completed",
        )
    )

    summary = registry.summarize_task_events(task_id="task-queued", task_type="retrieval_pack")

    transitions = {(item.from_status, item.to_status): item.total for item in summary.transitions}
    assert transitions[(None, "queued")] == 1
    assert transitions[("queued", "running")] == 1
    assert transitions[("running", "completed")] == 1


def test_task_service_summarize_tasks_returns_observability_aggregates() -> None:
    registry = InMemoryTaskRegistry()
    service = TaskApplicationService(
        registry=registry,
        checkpoint_store=LangGraphPostgresCheckpointStore(dsn=None, use_fallback_if_unset=True),
    )

    service.create_task(
        "retrieval_pack",
        initial_status="queued",
        initial_node="queued",
        details={
            "execution_mode": "async",
            "queue_name": "retrieval",
            "queued_at": "2026-04-26T10:00:00+00:00",
        },
    )
    running = service.create_task(
        "knowledge_indexing",
        initial_status="queued",
        initial_node="queued",
        details={
            "execution_mode": "async",
            "queue_name": "knowledge-indexing",
            "queued_at": "2026-04-26T10:00:00+00:00",
        },
    )
    service.update_task(
        running.task_id,
        status="running",
        current_node="start",
        details={
            **service.get_task(running.task_id).details,
            "execution_mode": "async",
            "queue_name": "knowledge-indexing",
            "started_at": "2026-04-26T10:00:03+00:00",
        },
    )
    completed = service.create_task(
        "authoring_pack",
        initial_status="queued",
        initial_node="queued",
        details={
            "execution_mode": "async",
            "queue_name": "authoring",
            "queued_at": "2026-04-26T10:00:00+00:00",
        },
    )
    service.update_task(
        completed.task_id,
        status="running",
        current_node="start",
        details={
            **service.get_task(completed.task_id).details,
            "execution_mode": "async",
            "queue_name": "authoring",
            "started_at": "2026-04-26T10:00:02+00:00",
        },
    )
    service.update_task(
        completed.task_id,
        status="completed",
        current_node="completed",
        details={
            **service.get_task(completed.task_id).details,
            "execution_mode": "async",
            "queue_name": "authoring",
            "completed_at": "2026-04-26T10:00:09+00:00",
        },
    )

    summary = service.summarize_tasks()

    assert summary.total_tasks == 3
    assert summary.queued_tasks == 1
    assert summary.running_tasks == 1
    assert summary.completed_tasks == 1
    assert summary.async_tasks == 3
    statuses = {item.status: item.total for item in summary.statuses}
    assert statuses["queued"] == 1
    assert statuses["running"] == 1
    assert statuses["completed"] == 1
    task_types = {item.task_type: item for item in summary.task_types}
    assert task_types["authoring_pack"].avg_queue_wait_ms == 2000
    assert task_types["knowledge_indexing"].avg_queue_wait_ms == 3000
