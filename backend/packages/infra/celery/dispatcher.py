from __future__ import annotations

from dataclasses import dataclass


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
