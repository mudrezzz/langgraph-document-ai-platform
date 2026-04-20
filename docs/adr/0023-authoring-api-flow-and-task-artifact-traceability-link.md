# ADR-0023: Authoring API Flow и task->artifact traceability link

- Статус: Accepted
- Дата: 2026-04-20

## Контекст

После `Increment 17` в системе уже были Retrieval/Repository/Artifact Writer MCP сервисы, но отсутствовал единый API flow, который:

- запускает authoring задачу поверх retrieval;
- формирует итоговый артефакт;
- сохраняет traceability между task, retrieval источниками и артефактом.

Без этого API boundary оставался retrieval-centric, а authoring сценарий требовал ручной оркестрации нескольких MCP инструментов.

## Решение

1. Добавить authoring API lifecycle:
   - `POST /api/v1/tasks/authoring/start`;
   - `GET /api/v1/tasks/{task_id}/artifact`.
2. Добавить `AuthoringApplicationService`:
   - orchestration `retrieval -> draft -> artifact`;
   - запись task checkpoint + details в общий lifecycle контур.
3. Ввести persistence link между задачей и артефактом:
   - таблица `app.task_artifacts` (миграция `0007_task_artifacts.sql`);
   - адаптер `PostgresTaskArtifactRegistry`.
4. Добавить traceability контракт в API:
   - `retrieval_task_id`;
   - `source_refs` (`doc_id/version/block_id`) для итогового артефакта.
5. Добавить smoke/demo для authoring API:
   - `smoke_authoring_api.sh/.ps1` (+ python runner);
   - `demo_release_authoring_traceability_case.sh/.ps1`.

## Последствия

Плюсы:

- появился минимальный end-to-end authoring flow на API boundary;
- traceability между task/evidence/artifact стала персистентной и читаемой через API;
- smoke/runbook покрывают новый authoring сценарий в `prod` profile.

Минусы:

- authoring draft пока rule-based (без отдельного LLM section writer/reviewer цикла);
- `task_artifacts` в MVP предполагает 1 artifact на task (PK по `task_id`);
- list/read-model для authoring артефактов пока offset-based и без отдельного dashboard слоя.
