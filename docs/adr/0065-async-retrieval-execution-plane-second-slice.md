# ADR-0065: Async Retrieval on Unified Execution Plane second slice

- Статус: Accepted
- Дата: 2026-04-26

## Контекст

После ADR-0064 unified execution plane уже покрывает authoring/HITL и knowledge indexing, но retrieval task lifecycle оставался синхронным special-case path. Это создавало архитектурный разрыв:

- retrieval является обязательным шагом почти всех production сценариев;
- task/events/checkpoint contracts уже едины, но queue-based execution для retrieval отсутствовал;
- ручной demo и Docker/Celery e2e не могли проверить, что execution plane реально покрывает основной retrieval workload.

Для Increment 29 нужен следующий минимальный slice: перевести retrieval на тот же async plane без ввода нового runtime слоя и без breaking changes sync API.

## Решение

1. Расширить existing async dispatcher plane новым портом `RetrievalAsyncDispatcher`.
2. Добавить runtime implementations:
   - `InlineRetrievalAsyncDispatcher` для dev/test;
   - `CeleryRetrievalAsyncDispatcher` для production-like queue execution.
3. Расширить `RetrievalApplicationService` методами:
   - `start_async(request, dispatcher=...)`;
   - `run_existing_task(task_id, request)`.
4. Оставить sync endpoint `POST /api/v1/tasks/retrieval/start` без изменения внешнего контракта.
5. Добавить совместимое расширение API: `POST /api/v1/tasks/retrieval/start_async`.
6. Выполнять queued execution через existing worker app:
   - Celery task `apps.worker.tasks.run_retrieval_task`;
   - отдельная queue `retrieval` через env `APP_CELERY_RETRIEVAL_QUEUE`.
7. Расширить docker-compose async worker так, чтобы один worker слушал очереди `authoring`, `knowledge-indexing`, `retrieval`.
8. Добавить operational smoke/demo scripts, чтобы async retrieval можно было проверить вручную в PostgreSQL/Celery контуре.

## Последствия

Плюсы:

- unified execution plane теперь покрывает все три основных long-running workflow: retrieval, knowledge indexing, authoring;
- sync API сохранен, а async retrieval добавлен как backward-compatible extension;
- task lifecycle, checkpoint и task events остаются едиными для sync/async retrieval paths;
- manual smoke и Docker/Celery e2e теперь подтверждают queue-backed retrieval path, а не только authoring/indexing.

Минусы:

- authoring пока по-прежнему вызывает retrieval синхронно внутри своего pipeline, то есть nested async orchestration еще не вводится;
- observability слой пока ограничен существующими task events/status details и не добавляет отдельные queue metrics;
- worker topology остается pragmatic single-worker/multi-queue layout для docker-compose acceptance контура.
