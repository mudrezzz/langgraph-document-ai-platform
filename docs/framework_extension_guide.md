# Framework Extension Guide

Дата обновления: 2026-04-24
Статус: Increment 26 complete; next Increment 27

## Назначение

Этот документ описывает стандартный путь расширения internal framework layer. Его цель - не заменить архитектурный blueprint, а дать короткий практический checklist для добавления новых workflows, tools, MCP services, adapters и domain packages без нарушения текущих границ.

## Базовые правила

1. Domain/application code зависит от framework contracts, а не от concrete infra adapters.
2. LangGraph остается runtime для orchestration; framework не вводит отдельный DSL.
3. Большие payloads не хранятся в workflow state, если их можно сохранить в store и передать по ref.
4. Внешние service boundaries используют Pydantic schemas из `packages/schemas`.
5. Любое расширение, влияющее на API, persistence, MCP или demo flow, обновляет README, SAO, ADR и release go/no-go demo.

## Как Добавить Workflow

1. Добавить typed state contract в `backend/packages/schemas/workflow` или доменный schema module.
2. Реализовать класс workflow через `framework.workflows.BaseWorkflow` или `SubgraphWorkflow`.
3. Для простого одношагового workflow описать `state_schema()`, `execute()` и при необходимости `execute_resume()`.
4. Для multi-node workflow переопределить `workflow_nodes(is_resume=...)` и вернуть список `WorkflowNodeSpec`.
5. Node handler должен принимать typed state и `WorkflowExecutionContext`; через context доступны `workflow_name`, `node_name`, `task_id`, `correlation_id`, `is_resume`, `metadata`.
6. Для reusable subgraph использовать `SubgraphWorkflow` и `invoke_as_subgraph(..., parent_context=...)`, если нужно передать parent workflow metadata.
7. Передавать `task_context.task_id` при использовании LangGraph checkpointer.
8. Передавать `task_context.correlation_id`, если workflow участвует в сквозной трассировке.
9. Если workflow должен попадать в audit/read-model, передать `WorkflowNodeEventSink` при создании workflow.
10. Для task lifecycle audit использовать `TaskApplicationService.build_workflow_node_event_sink()`.
11. Подключить workflow через application service или `WorkflowFactory`.
12. Если workflow требует dependencies, регистрировать builder:
   `factory.register_builder("key", lambda retriever: MyWorkflow(retriever=retriever), metadata={...})`.
13. Если workflow не требует dependencies, допустима обратно совместимая регистрация класса:
   `factory.register("key", MyWorkflow)`.
14. Для duplicate registration использовать явный `replace=True`; missing key и duplicate key должны обрабатываться через `WorkflowNotRegisteredError`/`WorkflowRegistrationError`.
15. Добавить unit tests:
   - invoke path;
   - resume path, если workflow resumable;
   - multi-node ordering и context propagation, если используется `workflow_nodes`;
   - node event payload, если подключен `WorkflowNodeEventSink`;
   - error/interrupt branch, если есть HITL;
   - checkpointer thread id behavior, если workflow long-running.

## Как Добавить Tool

1. Добавить Pydantic input/output schemas.
2. Реализовать `framework.tools.BaseTool`.
3. Зарегистрировать tool в `ToolRegistry`.
4. Вызывать tool через `ToolExecutor`, если он используется агентом/workflow.
5. Передавать `ToolContext` с `task_id`, `actor` и, если доступно, `node_name`, `correlation_id`, `idempotency_key`.
6. Настроить `ToolExecutionPolicy`, если tool требует retry/timeout/idempotency behavior.
7. Подключить `ToolExecutionAuditSink`, если tool call должен попадать в audit/read-model.
8. Добавить contract tests:
   - input validation;
   - output validation;
   - registry lookup;
   - execution context propagation.
   - retry/failure path, если используется retry policy;
   - idempotency cache path, если tool может повторно вызываться с тем же ключом;
   - audit record payload, если подключен audit sink.

## Как Добавить MCP Service

1. Добавить MCP schemas в `backend/packages/schemas/mcp`.
2. Реализовать service adapter от `framework.mcp.BaseFastMcpService`.
3. Сервис должен принимать application/domain service как dependency.
4. `metadata()` должен возвращать `service_name`, `version` и список tool names.
5. Добавить runtime entrypoint в `backend/apps/mcp_*`.
6. Добавить run/smoke scripts для Linux и Windows, если сервис ручной или демонстрационный.
7. Добавить tests на прямой service-call без запуска MCP runtime.

## Как Добавить Persistence Adapter

1. Начать с Protocol/contract в framework или application layer.
2. Реализовать concrete adapter в `backend/packages/infra`.
3. Если adapter пишет в PostgreSQL, добавить additive SQL migration.
4. Поддержать fallback только для `dev/stage`, если это совместимо с runtime profile policy.
5. Добавить tests:
   - in-memory/fallback behavior;
   - SQL payload mapping;
   - cursor/filter behavior, если это read-model.

## Как Добавить Domain Package

1. Создать пакет под `backend/packages/domain_*`.
2. Держать domain logic независимой от FastAPI, Celery и concrete DB clients.
3. Зависеть от framework contracts и Pydantic schemas.
4. Сборку concrete dependencies держать в bootstrap/factory module.
5. Application service должен быть тонким use-case boundary, а не местом для всей domain logic.

## Acceptance Checklist

Перед завершением инкремента:

- unit/integration/e2e tests зеленые;
- release go/no-go demo обновлен или явно не затронут;
- README отражает новые команды/API/contracts;
- SAO отражает текущий статус и GAP;
- ADR добавлен, если принято новое архитектурное решение;
- migration/runbook обновлены, если менялась БД или runtime topology.
