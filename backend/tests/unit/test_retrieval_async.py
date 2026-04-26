from __future__ import annotations

import pytest

from application.async_dispatcher import InlineRetrievalAsyncDispatcher
from application.canonical_document_service import CanonicalDocumentApplicationService
from application.errors import WorkflowExecutionError
from application.retrieval_service import RetrievalApplicationService
from application.task_service import InMemoryTaskRegistry, TaskApplicationService
from infra.postgres.canonical_document_store import PostgresCanonicalDocumentStore
from infra.postgres.checkpoint_store import LangGraphPostgresCheckpointStore
from schemas.api.contracts import StartRetrievalTaskRequest


def test_retrieval_application_service_start_async_with_inline_dispatcher() -> None:
    task_service = TaskApplicationService(
        registry=InMemoryTaskRegistry(),
        checkpoint_store=LangGraphPostgresCheckpointStore(dsn=None, use_fallback_if_unset=True),
    )
    service = RetrievalApplicationService(
        task_service=task_service,
        canonical_document_service=CanonicalDocumentApplicationService(
            store=PostgresCanonicalDocumentStore(use_fallback_if_unset=True)
        ),
    )
    dispatcher = InlineRetrievalAsyncDispatcher(
        runner=lambda task_id, payload: service.run_existing_task(
            task_id=task_id,
            request=StartRetrievalTaskRequest.model_validate(payload),
        )
    )

    started = service.start_async(
        StartRetrievalTaskRequest(
            query="async retrieval readiness",
            filters={"project_id": "p1"},
            task_context={"requester": "unit-test", "case_dataset_id": "saa_release_readiness"},
        ),
        dispatcher=dispatcher,
    )

    assert started.status == "queued"
    task = task_service.get_task(started.task_id)
    assert task.status == "completed"
    assert task.details["execution_mode"] == "async"
    assert task.details["dispatch_id"] == f"inline-retrieval-{started.task_id}"
    payload = task_service.get_state_payload(started.task_id)
    assert payload["task_context"]["task_id"] == started.task_id


def test_retrieval_application_service_start_async_marks_task_failed_on_dispatch_error() -> None:
    task_service = TaskApplicationService(
        registry=InMemoryTaskRegistry(),
        checkpoint_store=LangGraphPostgresCheckpointStore(dsn=None, use_fallback_if_unset=True),
    )
    service = RetrievalApplicationService(task_service=task_service)

    class _FailingDispatcher:
        def enqueue_retrieval_start(self, *, task_id: str, request_payload: dict) -> str:
            _ = task_id, request_payload
            raise RuntimeError("broker unavailable")

    with pytest.raises(WorkflowExecutionError, match="async очередь"):
        service.start_async(
            StartRetrievalTaskRequest(
                query="async retrieval readiness",
                filters={"project_id": "p1"},
                task_context={"requester": "unit-test"},
            ),
            dispatcher=_FailingDispatcher(),
        )

    tasks = task_service.list_tasks(limit=10, task_type="retrieval_pack")
    assert tasks.total_returned == 1
    task = tasks.items[0]
    assert task.status == "failed"
    assert task.details["execution_mode"] == "async"
    assert task.details["error"] == "broker unavailable"
