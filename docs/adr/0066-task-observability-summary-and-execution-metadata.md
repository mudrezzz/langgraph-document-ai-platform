# ADR-0066: Task Observability Summary and Execution Metadata on Unified Plane third slice

- Статус: Accepted
- Дата: 2026-04-26

## Контекст

После ADR-0064 и ADR-0065 unified async execution plane уже покрывает authoring, knowledge indexing и retrieval, но оператору все еще неудобно разбирать runtime состояние системы:

- `GET /api/v1/tasks` показывает только отдельные task rows;
- `GET /api/v1/tasks/events` и `/summary` показывают transitions, но не дают dashboard-friendly current-state aggregates;
- manual smoke/demo подтверждали только факт completion, а не execution trace (`queue`, `dispatch`, `correlation`, queue wait).

Для Increment 29 нужен минимальный observability slice поверх уже существующего read-model слоя, без новой telemetry-подсистемы.

## Решение

1. Расширить task lifecycle details execution metadata полями:
   - `correlation_id`;
   - `async_provider`;
   - `queue_name`;
   - `queued_at`;
   - `started_at`;
   - `completed_at`/`failed_at`;
   - `queue_wait_ms`.
2. Оставить эти поля в существующем `details` payload задачи, не вводя отдельную таблицу.
3. Добавить новый read-model endpoint `GET /api/v1/tasks/observability/summary`.
4. Считать агрегаты поверх existing task registry, а не поверх raw queue backend:
   - `total_tasks`;
   - counts по текущим статусам (`queued`, `running`, `waiting_human`, `completed`, `failed`);
   - `async_tasks`;
   - `avg_duration_ms`, `max_duration_ms`, `avg_queue_wait_ms`;
   - breakdown по `task_type`.
5. Ручные smoke/demo scripts должны выводить execution metadata и observability summary, чтобы оператор мог проверить unified execution plane вручную.

## Последствия

Плюсы:

- execution plane становится наблюдаемым без новой инфраструктуры metrics/logging;
- оператор видит не только transitions, но и текущую сводку по задачам и queue wait behavior;
- API остается backward-compatible: новые поля добавлены как расширение существующих details/read-model payloads.

Минусы:

- агрегаты строятся по состоянию task registry, а не по реальным внутренним метрикам брокера очередей;
- structured JSON logging и межсервисная log correlation еще не закрыты;
- для production dashboards при росте нагрузки может понадобиться отдельный pre-aggregated read model.
