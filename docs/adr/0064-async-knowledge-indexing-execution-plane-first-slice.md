# ADR-0064: Async Knowledge Indexing on Unified Execution Plane first slice

- Статус: Accepted
- Дата: 2026-04-26

## Контекст

После Increment 28 async execution plane уже существовал, но был фактически привязан только к authoring/HITL path через Celery + Redis. Increment 29 требует сделать execution plane общим для всех long-running workflows, не вводя при этом новую параллельную архитектуру.

Knowledge Indexing был следующим логичным кандидатом:

- это долгий workflow с файловым parsing, canonical persistence и embedding indexing;
- у него уже есть task lifecycle API (`POST /api/v1/tasks/knowledge-indexing/start`);
- он уже пишет task events и workflow node events;
- в release demo именно indexing является входом в production retrieval fabric.

Оставлять indexing только синхронным значило бы сохранить special-case execution behavior и не дать очереди/Celery покрыть ingestion path.

## Решение

1. Расширить существующий async dispatcher contract новым портом `KnowledgeIndexingAsyncDispatcher`.
2. Добавить два runtime implementation without new architecture branch:
   - `InlineKnowledgeIndexingAsyncDispatcher` для dev/test;
   - `CeleryKnowledgeIndexingAsyncDispatcher` для production-like async execution.
3. Расширить `KnowledgeIndexingApplicationService` методами:
   - `start_task_async(request, dispatcher=...)`;
   - `run_existing_task(task_id, request)`.
4. Добавить API endpoint `POST /api/v1/tasks/knowledge-indexing/start_async`.
5. Выполнять queued execution через existing worker app:
   - Celery task `apps.worker.tasks.run_knowledge_indexing_task`;
   - queue `knowledge-indexing` через env `APP_CELERY_INDEXING_QUEUE`.
6. Оставить sync endpoint `POST /api/v1/tasks/knowledge-indexing/start` без breaking changes.
7. Для Docker/Celery runtime нормализовать `source_paths` из host-path в worker-visible `/workspace/...` path, поскольку worker запускается в контейнере с bind mount volume.
8. Расширить worker image parser dependencies (`python-docx`, `PyMuPDF`), чтобы async knowledge indexing поддерживал те же `.docx/.pdf` fixtures, что и sync path.

## Последствия

Плюсы:

- execution plane перестает быть authoring-only и начинает покрывать ingestion path;
- release/demo контур теперь может прогонять canonical indexing через ту же очередь/Celery runtime, что и другие long-running workflows;
- task lifecycle и workflow node audit остаются едиными для sync/async path;
- публичный sync contract сохранен, а async path добавлен как совместимое расширение.

Минусы:

- unified execution plane пока все еще не обобщен на retrieval и quality evaluation;
- worker path normalization пока реализован как pragmatic mapping для docker-compose volume layout `/workspace`, а не как общий storage abstraction;
- Docker worker image теперь обязан содержать parser dependencies Knowledge Factory.
