# ADR-0067: Structured Runtime Logging and HITL Observability Summary

- Статус: Accepted
- Дата: 2026-04-26

## Контекст

После ADR-0066 execution plane уже стал наблюдаемым через task registry и `/api/v1/tasks/observability/summary`, но оставались два пробела:

- оператору не хватало структурированных runtime log lines по API, Celery worker и HITL continuation path;
- reviewer/HITL активность была доступна только как список действий через `GET /api/v1/hitl/actions`, без агрегированной сводки для dashboard/manual smoke.

Для Increment 29 нужен небольшой production-compatible срез, который не вводит отдельную telemetry stack и использует уже существующие read-model/persistence adapters.

## Решение

1. Добавить общий helper `infra.logging.runtime` для one-line JSON logging на stdlib `logging`.
2. Логировать ключевые execution events в трех runtime точках:
   - FastAPI start/submit endpoints;
   - Celery worker task start/completion/failure;
   - authoring/HITL orchestration events (`queued`, `waiting_human`, `processing`, `completed`, `rejected`).
3. Оставить correlation через existing `task.details.correlation_id`, `dispatch_id`, `queue_name`, а не вводить отдельный trace context store.
4. Расширить `HitlActionStore` методом `summarize_actions(...)` и добавить endpoint `GET /api/v1/hitl/observability/summary`.
5. Строить reviewer/HITL aggregates поверх existing `app.hitl_actions` read-model:
   - `total_actions`, `unique_tasks`;
   - pending/queued/processing/completed counts;
   - decision mix (`approve`, `needs_changes`, `reject`);
   - `avg_iteration`, `max_iteration`;
   - reviewer load breakdown.

## Последствия

Плюсы:

- оператор получает machine-readable JSON logs без внешней logging platform;
- troubleshooting async/HITL paths упрощается за счет единых полей `task_id`, `correlation_id`, `dispatch_id`, `queue_name`;
- reviewer activity становится видна через агрегированный API без новой таблицы/materialized view.

Минусы:

- logging пока ограничен API/worker/authoring paths и не охватывает все MCP runtime entrypoints;
- HITL summary строится по текущему read-model слою и пока не содержит периодических SLA buckets;
- для полноценных production dashboards позже может понадобиться отдельный metrics/log pipeline.
