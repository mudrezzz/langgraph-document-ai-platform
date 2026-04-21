# Design Note: Increment 22 (Iterative HITL + Async Continuation)

Дата: 2026-04-21

## 1. Problem statement

После `Increment 21` HITL был одношаговым:

- `waiting_human -> submit -> completed|failed`;
- не было итеративного цикла `needs_changes -> rewrite -> re-review -> waiting_human`;
- `hitl/submit` мог синхронно завершать pipeline в API-контексте;
- не было явной idempotency-защиты на повторный submit одного и того же решения.

Для production-подобного контура нужен управляемый async lifecycle и предсказуемая policy по итерациям.

## 2. Scope / Out of scope

Scope:

- добавить итеративный HITL loop с ограничением по количеству итераций;
- перевести continuation после `hitl/submit` в async dispatcher plane (inline/celery);
- ввести idempotency и optimistic guard (`expected_iteration`) для `hitl/submit`;
- расширить read-model HITL статуса (`iteration`, `max_iterations`, `deadline`, `pending_action`);
- обновить smoke/demo/tests/docs под новый lifecycle.

Out of scope:

- отдельный reviewer UI;
- сложная роль-модель (RBAC/SSO);
- внешний брокер событий (Kafka/NATS) и распределенный workflow orchestration beyond Celery.

## 3. Какие контракты меняются

API:

- `POST /api/v1/tasks/{task_id}/hitl/submit`:
  - добавлены `idempotency_key`, `expected_iteration`;
  - submit теперь может вернуть не только `completed`, но и `queued/running/waiting_human`.
- `GET /api/v1/tasks/{task_id}/hitl`:
  - добавлены `current_iteration`, `max_iterations`, `deadline_at`, `can_submit`, `pending_action_id`;
  - действия reviewer теперь содержат `action_id`, `iteration`, `status`, `idempotency_key`.

Internal async contract:

- `AuthoringAsyncDispatcher` расширен методом enqueue HITL-action continuation;
- Celery worker получил отдельный task для continuation после submit.

Схемы/миграции:

- SQL миграции не добавлялись в этом инкременте (MVP хранит историю HITL в checkpoint/task details).

## 4. Риски и совместимость

Совместимость:

- существующие endpoints сохранены;
- `idempotency_key` и `expected_iteration` опциональны;
- `start`/`start_async` контракты не ломаются.

Риски:

- повторные submit без idempotency key могут создавать новые action events;
- при ошибке постановки continuation в очередь нужен rollback в `waiting_human` (реализован);
- policy по `needs_changes` на финальной итерации может вызывать 409 (ожидаемое поведение, требует явного approve/reject).

## 5. Test plan

Unit:

- async submit + continuation через inline dispatcher;
- `needs_changes -> iteration+1`;
- idempotency replay на `idempotency_key`;
- блокировка `needs_changes` при достижении max iterations.

Integration:

- API flow `start_async -> waiting_human -> submit -> poll -> completed`;
- iterative flow с двумя итерациями и replay submit.

E2E:

- FastAPI e2e (in-process uvicorn);
- Postgres-backed e2e;
- Docker e2e для реального `PostgreSQL + Redis + Celery`.

Smoke/manual:

- async smoke обновлен для последовательности решений (`--hitl-decision-sequence needs_changes,approve`).

## 6. Rollout plan

1. Расширить схемы API/state и dispatcher контракты.
2. Добавить worker-task для HITL continuation.
3. Перевести submit на async continuation с rollback при enqueue-error.
4. Добавить iterative loop policy и idempotency.
5. Обновить тесты (unit/integration/e2e/docker-e2e).
6. Обновить runbook/docs/ADR.

## 7. Definition of Done

- итеративный HITL lifecycle работает: минимум 2 итерации (`needs_changes -> waiting_human(iteration+1) -> approve`);
- continuation после submit исполняется через async dispatcher (inline/celery);
- submit поддерживает idempotency и expected_iteration guard;
- тесты зеленые: unit + integration + e2e + docker async e2e;
- документация обновлена (`README`, `Architecture Overview`, `ADR`, manual smoke/runbook).
