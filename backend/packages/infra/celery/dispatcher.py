from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


def _normalize_worker_path(path: str) -> str:
    """Приводит host path к worker-visible path внутри docker compose volume."""

    if not path:
        return path

    raw = Path(path)
    if not raw.is_absolute():
        return path

    try:
        repo_root = Path(__file__).resolve().parents[4]
        relative = raw.relative_to(repo_root)
    except ValueError:
        return path

    return str(Path("/workspace") / relative)


def _normalize_worker_payload(payload: dict) -> dict:
    normalized = dict(payload)
    if "source_paths" in normalized:
        normalized["source_paths"] = [
            _normalize_worker_path(str(item)) for item in normalized.get("source_paths", [])
        ]
    return normalized


@dataclass(slots=True)
class CeleryAuthoringAsyncDispatcher:
    """Dispatcher постановки authoring задач в Celery очередь."""

    queue_name: str = "authoring"

    def enqueue_authoring_start(self, *, task_id: str, request_payload: dict) -> str:
        try:
            from apps.worker.tasks import run_authoring_task
        except Exception as exc:  # pragma: no cover - зависит от окружения рантайма
            raise RuntimeError(
                "Не удалось импортировать Celery worker task. Проверьте PYTHONPATH и зависимости worker-контейнера."
            ) from exc

        result = run_authoring_task.apply_async(
            kwargs={
                "task_id": task_id,
                "request_payload": request_payload,
            },
            queue=self.queue_name,
        )
        return str(result.id)

    def enqueue_hitl_action(self, *, task_id: str, action_payload: dict) -> str:
        try:
            from apps.worker.tasks import run_authoring_hitl_action
        except Exception as exc:  # pragma: no cover - зависит от окружения рантайма
            raise RuntimeError(
                "Не удалось импортировать Celery HITL task. Проверьте PYTHONPATH и зависимости worker-контейнера."
            ) from exc

        result = run_authoring_hitl_action.apply_async(
            kwargs={
                "task_id": task_id,
                "action_payload": action_payload,
            },
            queue=self.queue_name,
        )
        return str(result.id)


@dataclass(slots=True)
class CeleryKnowledgeIndexingAsyncDispatcher:
    """Dispatcher постановки knowledge indexing задач в Celery очередь."""

    queue_name: str = "knowledge-indexing"

    def enqueue_knowledge_indexing_start(self, *, task_id: str, request_payload: dict) -> str:
        try:
            from apps.worker.tasks import run_knowledge_indexing_task
        except Exception as exc:  # pragma: no cover - зависит от окружения рантайма
            raise RuntimeError(
                "Не удалось импортировать Celery knowledge indexing task. Проверьте PYTHONPATH и зависимости worker-контейнера."
            ) from exc

        result = run_knowledge_indexing_task.apply_async(
            kwargs={
                "task_id": task_id,
                "request_payload": _normalize_worker_payload(request_payload),
            },
            queue=self.queue_name,
        )
        return str(result.id)


@dataclass(slots=True)
class CeleryRetrievalAsyncDispatcher:
    """Dispatcher постановки retrieval задач в Celery очередь."""

    queue_name: str = "retrieval"

    def enqueue_retrieval_start(self, *, task_id: str, request_payload: dict) -> str:
        try:
            from apps.worker.tasks import run_retrieval_task
        except Exception as exc:  # pragma: no cover - зависит от окружения рантайма
            raise RuntimeError(
                "Не удалось импортировать Celery retrieval task. Проверьте PYTHONPATH и зависимости worker-контейнера."
            ) from exc

        result = run_retrieval_task.apply_async(
            kwargs={
                "task_id": task_id,
                "request_payload": request_payload,
            },
            queue=self.queue_name,
        )
        return str(result.id)
