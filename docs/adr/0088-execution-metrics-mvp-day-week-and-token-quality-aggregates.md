# ADR-0088: Execution Metrics MVP (day/week events + token/quality observability)

- Статус: Accepted
- Дата: 2026-04-29

## Контекст

К концу Increment 31 у нас уже были `task_events` и endpoint `GET /api/v1/tasks/observability/summary`, но для runtime-операций оставались пробелы:

- в summary событий не было периодных бакетов (day/week) для быстрых трендов;
- observability по задачам не включала quality/token метрики retrieval/authoring path;
- в task lifecycle details не было унифицированного `duration_ms`.

Для Increment 32 нужен минимальный metrics slice без отдельной telemetry БД и без breaking API changes.

## Решение

1. Расширить `GET /api/v1/tasks/events/summary` агрегатами:
   - `daily[]` и `weekly[]` со структурой:
     - `bucket_start`;
     - `total_events`;
     - `unique_tasks`.
2. Расширить `GET /api/v1/tasks/observability/summary` и per-task-type breakdown:
   - quality metrics:
     - `avg_selected_block_count`;
     - `avg_confidence`;
     - `tasks_with_unresolved_gaps`;
     - `unresolved_gaps_total`;
   - token metrics:
     - `llm_tokens_prompt_total`;
     - `llm_tokens_completion_total`;
     - `llm_tokens_total`.
3. В `TaskApplicationService` автоматически рассчитывать `duration_ms` при наличии `started_at` и `completed_at|failed_at`.
4. В authoring LLM path добавлять `llm_tokens_*` в draft metadata и task details:
   - использовать provider usage, если доступен;
   - при отсутствии usage применять lightweight fallback estimate.

## Последствия

Плюсы:

- операционный слой получает day/week тренды и базовые quality/token метрики без новой инфраструктуры;
- API расширен аддитивно и backward-compatible;
- runtime details становятся более пригодными для SLA/quality dashboards следующего слайса.

Минусы:

- token usage для некоторых gateways может быть оценочным;
- агрегаты по-прежнему считаются поверх task registry/state payload, а не над выделенной metrics warehouse.
