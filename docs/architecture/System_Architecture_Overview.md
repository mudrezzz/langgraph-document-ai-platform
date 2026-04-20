# System Architecture Overview

Дата обновления: 2026-04-19
Статус: Increment 10

## 1. Целевой архитектурный ориентир

Система строится по модели из `./docs`:

- LangGraph как единый orchestration runtime;
- OOP framework layer с типизированными контрактами;
- domain-пакеты поверх framework-абстракций;
- infra adapters с изоляцией concrete интеграций;
- FastAPI + FastMCP на сервисных границах;
- PostgreSQL + pgvector для состояния, метаданных и векторов.

## 2. Текущая реализация (Increment 10)

Реализовано:

- framework и schemas layer;
- `BaseWorkflow` с LangGraph-backed compile/invoke/resume;
- API boundary + task lifecycle + interrupt/resume ветки;
- baseline persistence adapters:
  - `PostgresDocumentRepository`;
  - `LangGraphPostgresCheckpointStore`;
  - `PgVectorStoreAdapter`;
  - `PostgresSettings` из env (`APP_DB_DSN`, `APP_DB_SCHEMA`, `APP_VECTOR_DIM`, `APP_RUNTIME_PROFILE`).
- runtime profiles:
  - `dev`, `stage`, `prod`;
  - fallback persistence разрешен в `dev/stage` и отключен в `prod`.
- baseline migrations:
  - `backend/migrations/0001_baseline.sql`;
  - `backend/migrations/0002_task_registry.sql`;
  - `backend/migrations/0003_task_events.sql`.
- API история задач:
  - `GET /api/v1/tasks`;
  - фильтры `status`, `task_type`, `from`, `to`;
  - курсорная пагинация (`cursor`, `next_cursor`, `has_more`);
  - сортировка по `updated_at DESC, task_id DESC`.
- API аудит событий задач:
  - `GET /api/v1/tasks/events`;
  - фильтры `task_id`, `task_type`, `from`, `to`;
  - курсорная пагинация (`cursor`, `next_cursor`, `has_more`);
  - сортировка по `created_at DESC, event_id DESC`.
- аудит переходов статусов задач:
  - таблица `app.task_events`;
  - событие пишется при создании задачи и каждой смене `status`.
- архитектурное решение зафиксировано в:
  - `docs/adr/0013-runtime-profiles-task-history-cursor-and-status-audit.md`.
  - `docs/adr/0014-task-events-api-and-demo-runbook-hardening.md`.
  - `docs/adr/0015-smoke-keep-server-mode-for-post-smoke-api-validation.md`.
- локальный PostgreSQL deployment профиль:
  - `backend/docker-compose.postgres.yml`;
  - scripts: `postgres_up/down/migrate` (`.ps1` + `.sh`), `apply_migrations` (`.ps1` + `.sh`), smoke/demo.
  - в `smoke_retrieval_api.sh` добавлен режим `--keep-server` для ручной post-smoke проверки API.
- тестовое покрытие:
  - unit + integration + e2e;
  - e2e с реальным PostgreSQL: `test_fastapi_retrieval_e2e_postgres.py`;
  - smoke сценарий: `backend/scripts/smoke_retrieval_api.sh`.
- референсный реалистичный кейс:
  - `saa_release_readiness_case` с тестовыми knowledge layers;
  - end-to-end демонстрация через `demo_saa_release_readiness_case.ps1/.sh` (исправлен Linux parsing output).

## 3. Архитектурные ограничения текущей версии

- нет реального LangGraph checkpointer integration поверх production-grade PostgreSQL saver;
- отсутствуют рабочие FastMCP runtime-сервисы;
- отсутствуют `domain_docs` / `domain_authoring` workflows;
- API по-прежнему синхронный, без очередей long-running задач;
- нет полноценного production deployment runbook с эксплуатационными SLO/SLI метриками.

## 4. GAP к целевой архитектуре

1. Подключить реальный checkpointing LangGraph в PostgreSQL с восстановлением после process restart.
2. Поднять FastMCP сервисы по контрактам blueprint (`Retrieval MCP`, `Repository MCP`, `Artifact Writer MCP`).
3. Расширить API `task_events` дополнительными фильтрами (`to_status`, `from_status`) и агрегированными представлениями.
4. Ввести async/queue execution для long-running задач и retry-политику.
5. Собрать production deployment-профиль для Ubuntu 24: конфигурации, секреты, мониторинг, runbook.
6. Развить ingestion/template/authoring/assembly workflows.
7. Добавить observability/metrics/audit dashboards.

## 5. План следующего инкремента

1. Реализовать production checkpointer для LangGraph поверх PostgreSQL.
2. Подготовить первый FastMCP runtime сервис (`Retrieval MCP`) на FastMCP.
3. Зафиксировать deployment smoke/runbook для Ubuntu 24 c `stage`/`prod` профилями.
4. Расширить reference-case `saa_release_readiness` шагом authoring + traceability.
5. Добавить API/read-model для агрегированных audit-метрик по `task_events`.
