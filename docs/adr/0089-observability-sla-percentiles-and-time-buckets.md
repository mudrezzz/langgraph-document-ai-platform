# ADR-0089: Observability SLA percentiles and time buckets

- Статус: Accepted
- Дата: 2026-04-29

## Контекст

После ADR-0088 у нас появились quality/token execution metrics и day/week агрегаты `task_events`, но для SLA-контроля не хватало:

- percentiles (`p50/p95`) по длительности и queue wait;
- breach counters относительно SLA порогов;
- периодных day/week срезов для SLA состояния execution plane.

Нужно закрыть этот пробел без новой telemetry БД и без breaking API contracts.

## Решение

1. Расширить `TaskObservabilitySummary` и API `GET /api/v1/tasks/observability/summary`:
   - overall:
     - `p50_duration_ms`, `p95_duration_ms`;
     - `p50_queue_wait_ms`, `p95_queue_wait_ms`;
     - `duration_sla_threshold_ms`, `queue_wait_sla_threshold_ms`;
     - `duration_sla_breaches_total`, `queue_wait_sla_breaches_total`;
   - per task type:
     - те же percentile/breach поля.
2. Добавить периодные срезы observability:
   - `daily[]` и `weekly[]`:
     - `bucket_start`;
     - `total_tasks`, `completed_tasks`, `failed_tasks`, `waiting_human_tasks`;
     - `duration_sla_breaches_total`, `queue_wait_sla_breaches_total`.
3. SLA thresholds брать из env:
   - `APP_SLA_TASK_DURATION_MS`;
   - `APP_SLA_QUEUE_WAIT_MS`;
   - значения `<=0` или невалидные значения трактуются как `disabled`.
4. Оставить вычисления на текущем task read-model уровне (`app.tasks`/fallback), без нового хранилища.

## Последствия

Плюсы:

- появляется базовая SLA-видимость execution plane для ops/release gate;
- day/week динамика и percentile метрики доступны через уже существующий API;
- решение аддитивное, обратная совместимость сохранена.

Минусы:

- метрики считаются по текущему task read-model, а не по raw queue/runtime telemetry;
- для большого объема задач в будущем может понадобиться pre-aggregated materialized слой.
