# System Architecture Overview

Дата обновления: 2026-04-20
Статус: Increment 11

## 1. Целевой архитектурный ориентир

Система строится по модели из `./docs`:

- LangGraph как единый orchestration runtime;
- OOP framework layer с типизированными контрактами;
- domain-пакеты поверх framework-абстракций;
- infra adapters с изоляцией concrete интеграций;
- FastAPI + FastMCP на сервисных границах;
- PostgreSQL + pgvector для состояния, метаданных и векторов.

## 2. Текущая реализация (Increment 11)

Реализовано:

- framework и schemas layer;
- `BaseWorkflow` с LangGraph-backed compile/invoke/resume;
- API boundary + task lifecycle + interrupt/resume ветки;
- persistence adapters:
  - `PostgresDocumentRepository`;
  - `LangGraphPostgresCheckpointStore`;
  - `PgVectorStoreAdapter`;
  - `PostgresSettings` из env (`APP_DB_DSN`, `APP_DB_SCHEMA`, `APP_VECTOR_DIM`, `APP_RUNTIME_PROFILE`).
- runtime profiles:
  - `dev`, `stage`, `prod`;
  - fallback persistence разрешен в `dev/stage` и отключен в `prod`.
- SQL migrations:
  - `backend/migrations/0001_baseline.sql`;
  - `backend/migrations/0002_task_registry.sql`;
  - `backend/migrations/0003_task_events.sql`.
- task history API:
  - `GET /api/v1/tasks`;
  - фильтры `status`, `task_type`, `from`, `to`;
  - курсорная пагинация (`cursor`, `next_cursor`, `has_more`);
  - сортировка `updated_at DESC, task_id DESC`.
- task events API:
  - `GET /api/v1/tasks/events`;
  - фильтры `task_id`, `task_type`, `from`, `to`;
  - курсорная пагинация (`cursor`, `next_cursor`, `has_more`);
  - сортировка `created_at DESC, event_id DESC`.
- аудит переходов статусов:
  - таблица `app.task_events`;
  - событие при создании задачи и при каждой смене `status`.
- production checkpointer для LangGraph:
  - `PostgresLangGraphCheckpointer` реализует `BaseCheckpointSaver`;
  - использует таблицу `app.checkpoints` с namespaced `run_id` (`lg_thread:*`);
  - `BaseWorkflow` передает `configurable.thread_id` из `task_context.task_id`;
  - retrieval `start/resume` гарантируют наличие `task_id` в `task_context`.
- локальный PostgreSQL deployment профиль:
  - `backend/docker-compose.postgres.yml`;
  - scripts: `postgres_up/down/migrate` (`.ps1` + `.sh`), `apply_migrations` (`.ps1` + `.sh`), smoke/demo.
  - в `smoke_retrieval_api.sh` есть режим `--keep-server`.
- тестовое покрытие:
  - unit + integration + e2e;
  - e2e с реальным PostgreSQL: `test_fastapi_retrieval_e2e_postgres.py`;
  - smoke сценарий: `backend/scripts/smoke_retrieval_api.sh`.
- архитектурные решения:
  - `docs/adr/0013-runtime-profiles-task-history-cursor-and-status-audit.md`;
  - `docs/adr/0014-task-events-api-and-demo-runbook-hardening.md`;
  - `docs/adr/0015-smoke-keep-server-mode-for-post-smoke-api-validation.md`;
  - `docs/adr/0016-langgraph-postgres-checkpointer-runtime-integration.md`.

## 3. Архитектурные ограничения текущей версии

- checkpoint data и task payload пока сосуществуют в одной таблице `app.checkpoints`;
- отсутствуют рабочие FastMCP runtime-сервисы;
- отсутствуют `domain_docs` / `domain_authoring` workflows;
- API синхронный, без очередей long-running задач;
- нет полноценного production deployment runbook с эксплуатационными SLO/SLI метриками.

## 4. GAP к целевой архитектуре

1. Выделить checkpoint storage в отдельную схему/таблицы и добавить стратегии retention/pruning.
2. Поднять FastMCP сервисы по контрактам blueprint (`Retrieval MCP`, `Repository MCP`, `Artifact Writer MCP`).
3. Расширить API `task_events` дополнительными фильтрами (`to_status`, `from_status`) и агрегированными представлениями.
4. Ввести async/queue execution для long-running задач и retry-политику.
5. Собрать production deployment-профиль для Ubuntu 24: конфигурации, секреты, мониторинг, runbook.
6. Развить ingestion/template/authoring/assembly workflows.
7. Добавить observability/metrics/audit dashboards.

## 5. План следующего инкремента

1. Вынести LangGraph checkpoints в выделенный storage-контур (с миграцией схемы и cleanup-политиками).
2. Подготовить первый FastMCP runtime сервис (`Retrieval MCP`) на FastMCP.
3. Зафиксировать deployment smoke/runbook для Ubuntu 24 c `stage`/`prod` профилями.
4. Расширить reference-case `saa_release_readiness` шагом authoring + traceability.
5. Добавить API/read-model для агрегированных audit-метрик по `task_events`.
