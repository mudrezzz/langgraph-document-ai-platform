# Framework Extension Guide

Дата обновления: 2026-04-23
Статус: Increment 24

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
3. Описать `state_schema()`, `execute()` и при необходимости `execute_resume()`.
4. Передавать `task_context.task_id` при использовании LangGraph checkpointer.
5. Подключить workflow через application service или domain bootstrap factory.
6. Добавить unit tests:
   - invoke path;
   - resume path, если workflow resumable;
   - error/interrupt branch, если есть HITL;
   - checkpointer thread id behavior, если workflow long-running.

## Как Добавить Tool

1. Добавить Pydantic input/output schemas.
2. Реализовать `framework.tools.BaseTool`.
3. Зарегистрировать tool в `ToolRegistry`.
4. Вызывать tool через `ToolExecutor`, если он используется агентом/workflow.
5. Добавить contract tests:
   - input validation;
   - output validation;
   - registry lookup;
   - execution context propagation.

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
