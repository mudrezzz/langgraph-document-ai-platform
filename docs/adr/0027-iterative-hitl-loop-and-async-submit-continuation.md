# ADR-0027: Iterative HITL loop и async continuation после submit

- Статус: Accepted
- Дата: 2026-04-21

## Контекст

В `Increment 21` HITL был одношаговым:

- reviewer submit приводил задачу к финалу (completed/failed) в одном переходе;
- continuation мог выполняться синхронно в API-контексте;
- не было защищенного idempotency-механизма на повторные submit;
- не было явного лимита итераций `needs_changes`.

Для расширения authoring-процесса нужен управляемый итеративный контур и предсказуемое async поведение.

## Решение

1. Ввести итеративный HITL lifecycle:
   - поля state: `hitl_iteration`, `hitl_max_iterations`, `hitl_deadline_at`, `hitl_pending_action_id`;
   - policy: `needs_changes` разрешен только пока `iteration < max_iterations`;
   - `needs_changes` запускает rewrite + reviewer rerun и возвращает задачу в `waiting_human` с `iteration + 1`.
2. Вынести continuation после `hitl/submit` в async dispatcher plane:
   - новый dispatcher method `enqueue_hitl_action`;
   - новый Celery worker task `run_authoring_hitl_action`;
   - rollback в `waiting_human` при ошибке enqueue.
3. Добавить optimistic/idempotent защиту submit:
   - `idempotency_key` для dedup повторных запросов;
   - `expected_iteration` для защиты от stale submit.
4. Расширить HITL read-model:
   - `GET /api/v1/tasks/{task_id}/hitl` возвращает iteration/max/deadline/can_submit/pending_action + расширенную историю действий.

## Последствия

Плюсы:

- reviewer loop стал итеративным и контролируемым;
- API не блокируется финализацией после submit в async-профиле;
- снижен риск двойной обработки из-за сетевых retries.

Минусы:

- логика состояния стала сложнее (больше переходов и edge-cases);
- без отдельной SQL таблицы HITL-аудит хранится внутри checkpoint/details (MVP);
- policy `needs_changes` на финальной итерации требует явного approve/reject и может возвращать 409.
