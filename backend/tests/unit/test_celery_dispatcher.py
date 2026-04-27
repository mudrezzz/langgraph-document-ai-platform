from infra.celery.dispatcher import CeleryRetrievalAsyncDispatcher, _normalize_worker_path, _normalize_worker_payload


def test_normalize_worker_path_maps_repo_host_path_to_workspace() -> None:
    host = "/root/langgraph-document-ai-platform/backend/examples/cases/release_go_no_go_multifile_case/input"
    assert _normalize_worker_path(host) == "/workspace/backend/examples/cases/release_go_no_go_multifile_case/input"


def test_normalize_worker_path_leaves_non_repo_path_unchanged() -> None:
    host = "/tmp/outside-repo/input"
    assert _normalize_worker_path(host) == host


def test_normalize_worker_payload_updates_source_paths_only() -> None:
    payload = {
        "source_paths": [
            "/root/langgraph-document-ai-platform/backend/examples/cases/release_go_no_go_multifile_case/input",
            "/tmp/outside-repo/input",
        ],
        "task_context": {"requester": "unit-test"},
    }

    normalized = _normalize_worker_payload(payload)

    assert normalized["source_paths"] == [
        "/workspace/backend/examples/cases/release_go_no_go_multifile_case/input",
        "/tmp/outside-repo/input",
    ]
    assert normalized["task_context"] == {"requester": "unit-test"}


def test_normalize_worker_payload_keeps_document_version() -> None:
    payload = {
        "source_paths": ["/root/langgraph-document-ai-platform/backend/examples/cases/release_go_no_go_multifile_case/input"],
        "document_version": "3",
        "task_context": {"requester": "unit-test"},
    }

    normalized = _normalize_worker_payload(payload)

    assert normalized["source_paths"] == [
        "/workspace/backend/examples/cases/release_go_no_go_multifile_case/input"
    ]
    assert normalized["document_version"] == "3"
    assert normalized["task_context"] == {"requester": "unit-test"}


class _FakeAsyncResult:
    def __init__(self, task_id: str) -> None:
        self.id = task_id


class _FakeCeleryTask:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def apply_async(self, *, kwargs: dict, queue: str):
        self.calls.append({"kwargs": kwargs, "queue": queue})
        return _FakeAsyncResult("celery-dispatch-1")


def test_celery_retrieval_dispatcher_enqueues_task(monkeypatch) -> None:
    fake_task = _FakeCeleryTask()

    import apps.worker.tasks as worker_tasks

    monkeypatch.setattr(worker_tasks, "run_retrieval_task", fake_task)
    dispatcher = CeleryRetrievalAsyncDispatcher(queue_name="retrieval")

    dispatch_id = dispatcher.enqueue_retrieval_start(
        task_id="task-1",
        request_payload={
            "query": "async retrieval",
            "filters": {"project_id": "p1"},
            "task_context": {"requester": "unit-test"},
        },
    )

    assert dispatch_id == "celery-dispatch-1"
    assert fake_task.calls == [
        {
            "kwargs": {
                "task_id": "task-1",
                "request_payload": {
                    "query": "async retrieval",
                    "filters": {"project_id": "p1"},
                    "task_context": {"requester": "unit-test"},
                },
            },
            "queue": "retrieval",
        }
    ]
