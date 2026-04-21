# ADR-0026: Celery + Redis async authoring и HITL MVP

- Статус: Accepted
- Дата: 2026-04-21

## Контекст

После `Increment 20` authoring flow был multi-step, но выполнялся синхронно в API запросе.

Это создавало ограничения:

- long-running authoring блокировал HTTP request;
- не было очереди и retry-политики для фонового запуска;
- HITL требовал ручной оркестрации вне API.

## Решение

1. Ввести async запуск authoring через Celery/Redis:
   - endpoint `POST /api/v1/tasks/authoring/start_async`;
   - worker task `apps.worker.tasks.run_authoring_task`;
   - dispatcher policy через `APP_ASYNC_PROVIDER=inline|celery`.
2. Принять stack для очереди:
   - Celery как task runner;
   - Redis как broker/result backend;
   - Docker compose для runtime: `backend/docker-compose.async.yml`.
3. Добавить HITL MVP на API boundary:
   - статус задачи `waiting_human`;
   - `GET /api/v1/tasks/{task_id}/hitl`;
   - `POST /api/v1/tasks/{task_id}/hitl/submit` (`approve|needs_changes|reject`).
4. Сохранить обратную совместимость:
   - синхронный `POST /api/v1/tasks/authoring/start` остается рабочим;
   - `inline` dispatcher используется по умолчанию в local test/runtime.

## Последствия

Плюсы:

- long-running authoring можно запускать через очередь без блокировки API;
- появился базовый HITL lifecycle в рамках существующих API контрактов;
- dockerized контур Redis/Celery воспроизводим на сервере аналогично PostgreSQL.

Минусы:

- HITL пока одношаговый (без полноценной iterative re-review loop);
- retry-политика ограничена worker task уровнем и требует дальнейшего hardening;
- async plane пока покрывает только authoring контур.
