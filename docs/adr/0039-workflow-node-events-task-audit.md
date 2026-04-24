# ADR-0039: Workflow node events в task audit

- Статус: Accepted
- Дата: 2026-04-24

## Контекст

ADR-0038 добавил `WorkflowNodeSpec` и `WorkflowExecutionContext`, но observability все еще была только на уровне переходов статусов задач. Для production troubleshooting этого недостаточно: задача может оставаться в статусе `running`, а оператору нужно видеть, какой graph node стартовал, завершился или упал.

Новая схема БД не обязательна: `app.task_events` уже содержит `from_current_node`, `to_current_node` и JSONB `event_payload`.

## Решение

1. Добавить framework event contract:
   - `WorkflowNodeEventRecord`;
   - `WorkflowNodeEventSink`.
2. `BaseWorkflow` эмитит события вокруг каждого node:
   - `started`;
   - `completed`;
   - `failed`.
3. Добавить application adapter `TaskWorkflowNodeEventSink`.
4. Мапить node events в существующую таблицу `app.task_events`:
   - `from_status` и `to_status` равны текущему статусу задачи;
   - `from_current_node` равен текущему `task.current_node`;
   - `to_current_node` равен имени workflow node;
   - `event_payload.event_kind = "workflow_node"`;
   - payload содержит `workflow_name`, `node_name`, `node_status`, `is_resume`, `correlation_id`, `metadata`, `error`.
5. Подключить node event sink к retrieval и knowledge-indexing workflows.
6. Не менять внешний API:
   - `GET /api/v1/tasks/events` уже возвращает `event_payload`;
   - фильтры `from_status/to_status/task_id/task_type` продолжают работать.

## Последствия

Плюсы:

- появляется node-level audit без новой миграции и без изменения API schemas;
- status transition events и node events живут в одном cursor/read-model API;
- demo/smoke может проверять graph-node activity через existing task events endpoint;
- следующий observability slice может строить агрегаты поверх `event_payload.event_kind`.

Минусы:

- summary endpoint пока группирует все events по `from_status/to_status`, поэтому node events вида `running -> running` могут увеличивать `total_events`;
- отдельного фильтра `event_kind` в API пока нет, чтобы не менять внешний контракт в этом slice.
