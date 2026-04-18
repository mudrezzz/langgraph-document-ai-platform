# System Architecture Overview

Дата обновления: 2026-04-18
Статус: Increment 6

## 1. Целевой архитектурный ориентир

Система строится по модели из `./docs`:

- LangGraph как единый orchestration runtime;
- OOP framework layer с типизированными контрактами;
- domain-пакеты поверх framework-абстракций;
- infra adapters с изоляцией concrete интеграций;
- FastAPI + FastMCP на сервисных границах;
- PostgreSQL + pgvector для состояния, метаданных и векторов.

## 2. Текущая реализация (Increment 6)

Реализовано:

- framework и schemas layer;
- `BaseWorkflow` с LangGraph-backed compile/invoke/resume;
- API boundary + task lifecycle + interrupt/resume ветки;
- baseline persistence adapters:
  - `PostgresDocumentRepository`;
  - `LangGraphPostgresCheckpointStore`;
  - `PgVectorStoreAdapter`;
  - `PostgresSettings` из env (`APP_DB_DSN`, `APP_DB_SCHEMA`, `APP_VECTOR_DIM`).
- baseline migration:
  - `backend/migrations/0001_baseline.sql`;
  - scripts: `apply_migrations.py` и `apply_migrations.ps1`.
- локальный PostgreSQL deployment профиль:
  - `backend/docker-compose.postgres.yml`;
  - `backend/.env.example`;
  - scripts: `postgres_up.ps1`, `postgres_migrate.ps1`, `postgres_down.ps1`.
- тестовое покрытие:
  - unit + integration + e2e;
  - smoke и demo scripts;
  - e2e с реальным PostgreSQL: `test_fastapi_retrieval_e2e_postgres.py`.
- референсный реалистичный кейс:
  - `saa_release_readiness_case` с тестовыми knowledge layers;
  - end-to-end демонстрация через `demo_saa_release_readiness_case.ps1`.
- надежность e2e фикстур:
  - добавлена диагностика раннего падения `uvicorn` (stdout/stderr);
  - добавлены retry-safe проверки `/health` при connection refused во время старта.

## 3. Архитектурные ограничения текущей версии

- persistence adapters имеют fallback-режим для dev/test, а не строгий production-only режим;
- нет реального LangGraph checkpointer integration поверх PostgreSQL saver;
- отсутствуют рабочие FastMCP runtime-сервисы;
- отсутствуют `domain_docs` / `domain_authoring` workflows;
- API по-прежнему синхронный, без очередей long-running задач;
- `TaskRegistry` пока in-memory и не переживает перезапуск процесса.

## 4. GAP к целевой архитектуре

1. Нужен production-режим без in-memory fallback для critical paths.
2. Нужен реальный checkpointing LangGraph в PostgreSQL с восстановлением после process restart.
3. Нужны FastMCP сервисы по контрактам blueprint (`Retrieval MCP`, `Repository MCP`, `Artifact Writer MCP`).
4. Нужен персистентный task registry для статусов и метаданных задач.
5. Нужны ingestion/template/authoring/assembly workflows.
6. Нужны observability/audit/metrics и эксплуатационные dashboards.

## 5. План следующего инкремента

1. Подключить LangGraph checkpointer к PostgreSQL persistence.
2. Ввести явные runtime профили (`dev`, `stage`, `prod`) с отключением fallback в `prod`.
3. Поднять первые runtime MCP сервисы (`Retrieval MCP`, `Repository MCP`) на FastMCP.
4. Вынести `TaskRegistry` в persistence слой и добавить API-контракты для историчности задач.
5. Углубить референсный кейс `saa_release_readiness`: добавить authoring шаг и проверку traceability.
