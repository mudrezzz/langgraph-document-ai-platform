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
- `BaseWorkflow` с LangGraph-backed compile/invoke/resume;
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
- тестовое покрытие:
  - unit tests;
  - integration tests на endpoint-ы, включая error/interrupt/resume ветки;
  - smoke script для реального HTTP прогона.

## 3. Архитектурные ограничения текущей версии

- LangGraph интегрирован как runtime-движок базового workflow, но без checkpointer/postgres saver;
- adapters используют in-memory поведение вместо production DB/serving;
- API работает синхронно в рамках одного процесса;
- нет FastMCP runtime-серверов, есть только framework-base;
- domain_docs/domain_authoring и связанные workflows пока не реализованы.

## 4. GAP к целевой архитектуре

1. Нет production persistence слоя на реальном PostgreSQL/pgvector.
2. Нет полноценных MCP сервисов по контрактам из blueprint.
3. Нет ingestion/authoring/assembly workflows.
4. Нет эксплуатационного слоя observability/audit/metrics.
5. Нет multi-service deployment topology и очередей long-running задач.

## 5. План следующего инкремента

1. Реализовать PostgreSQL/pgvector-backed adapters вместо in-memory skeleton.
2. Подключить LangGraph checkpointing к persistence слою.
3. Добавить первые FastMCP runtime-сервисы (`Retrieval MCP`, `Repository MCP`).
4. Подготовить API scaffold для `ingestion` и `authoring` задач.