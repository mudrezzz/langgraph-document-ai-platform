# System Architecture Overview

Дата обновления: 2026-04-17
Статус: Increment 4

## 1. Целевой архитектурный ориентир

Система строится по модели из `./docs`:

- LangGraph как единый orchestration runtime;
- OOP framework layer с типизированными контрактами;
- domain-пакеты поверх framework-абстракций;
- infra adapters с изоляцией concrete интеграций;
- FastAPI + FastMCP на сервисных границах;
- PostgreSQL + pgvector для состояния, метаданных и векторов.

## 2. Текущая реализация (Increment 4)

Реализовано:

- framework и schemas layer;
- concrete adapter skeleton (`vLLM`, `TEI`, `postgres`, `pgvector`, `retrieval`);
- рабочий `RetrievalPackWorkflow` и bootstrap wiring;
- application services:
  - `TaskApplicationService`;
  - `RetrievalApplicationService`.
- API boundary (`apps/api/main.py`) с endpoint-ами:
  - `POST /api/v1/tasks/retrieval/start`;
  - `GET /api/v1/tasks/{task_id}`;
  - `GET /api/v1/tasks/{task_id}/evidence`;
  - `POST /api/v1/tasks/{task_id}/resume`;
  - `GET /health`.
- test coverage:
  - unit tests;
  - integration tests на каждый endpoint;
  - smoke script для реального HTTP прогона.

## 3. Архитектурные ограничения текущей версии

- BaseWorkflow пока не подключен к реальному LangGraph graph execution;
- adapters используют in-memory поведение вместо production DB/serving;
- API работает синхронно в рамках одного процесса;
- нет FastMCP runtime-серверов, есть только framework-base;
- domain_docs/domain_authoring и связанные workflows пока не реализованы.

## 4. GAP к целевой архитектуре

1. Нет фактической runtime-интеграции с LangGraph compile/invoke/resume.
2. Нет production persistence слоя на реальном PostgreSQL/pgvector.
3. Нет полноценных MCP сервисов по контрактам из blueprint.
4. Нет ingestion/authoring/assembly workflows.
5. Нет эксплуатационного слоя observability/audit/metrics.

## 5. План следующего инкремента

1. Расширить `BaseWorkflow` до интеграции с LangGraph graph builder.
2. Добавить error branches и interrupt/resume ветки в integration tests.
3. Реализовать persistence adapters с реальными SQL слоями.
4. Подготовить API scaffold для `ingestion` и `authoring` задач.