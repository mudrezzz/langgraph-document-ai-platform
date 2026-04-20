# System Architecture Overview

Дата обновления: 2026-04-20
Статус: Increment 13

## 1. Целевой архитектурный ориентир

Система строится по модели из `./docs`:

- LangGraph как единый orchestration runtime;
- OOP framework layer с типизированными контрактами;
- domain-пакеты поверх framework-абстракций;
- infra adapters с изоляцией concrete интеграций;
- FastAPI + FastMCP на сервисных границах;
- PostgreSQL + pgvector для состояния, метаданных и векторов.

## 2. Текущая реализация (Increment 13)

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
  - `backend/migrations/0003_task_events.sql`;
  - `backend/migrations/0004_langgraph_checkpoint_storage.sql`;
  - `backend/migrations/0005_task_events_status_filter_indexes.sql`.
- task history API:
  - `GET /api/v1/tasks`;
  - фильтры `status`, `task_type`, `from`, `to`;
  - курсорная пагинация (`cursor`, `next_cursor`, `has_more`);
  - сортировка `updated_at DESC, task_id DESC`.
- task events API:
  - `GET /api/v1/tasks/events`;
  - фильтры `task_id`, `task_type`, `from_status`, `to_status`, `from`, `to`;
  - курсорная пагинация (`cursor`, `next_cursor`, `has_more`);
  - сортировка `created_at DESC, event_id DESC`.
- task events summary API:
  - `GET /api/v1/tasks/events/summary`;
  - фильтры `task_id`, `task_type`, `from_status`, `to_status`, `from`, `to`;
  - агрегаты `total_events`, `unique_tasks`, `transitions(from_status,to_status,total)`.
- аудит переходов статусов:
  - таблица `app.task_events`;
  - событие при создании задачи и при каждой смене `status`.
- production checkpointer для LangGraph:
  - `PostgresLangGraphCheckpointer` реализует `BaseCheckpointSaver`;
  - runtime storage в таблицах `app.langgraph_checkpoints`, `app.langgraph_checkpoint_blobs`, `app.langgraph_checkpoint_writes`;
  - поддержаны операции `delete_thread`, `copy_thread`, `prune(strategy=keep_latest|delete)`;
  - `BaseWorkflow` передает `configurable.thread_id` из `task_context.task_id`.
- локальный PostgreSQL deployment профиль:
  - `backend/docker-compose.postgres.yml`;
  - scripts: `postgres_up/down/migrate` (`.ps1` + `.sh`), `apply_migrations` (`.ps1` + `.sh`), smoke/demo.
  - smoke/demo дополнены проверкой `events/summary`.
- тестовое покрытие:
  - unit + integration + e2e;
  - e2e с реальным PostgreSQL: `test_fastapi_retrieval_e2e_postgres.py`;
  - smoke сценарий: `backend/scripts/smoke_retrieval_api.sh`.
- архитектурные решения:
  - `docs/adr/0016-langgraph-postgres-checkpointer-runtime-integration.md`;
  - `docs/adr/0017-dedicated-langgraph-checkpoint-storage.md`;
  - `docs/adr/0018-task-events-status-filters-and-summary-read-model.md`.

## 3. Архитектурные ограничения текущей версии

- FastMCP runtime-сервисы пока отсутствуют;
- отсутствуют `domain_docs` / `domain_authoring` workflows;
- API синхронный, без очередей long-running задач;
- нет полноценного production deployment runbook с эксплуатационными SLO/SLI метриками;
- нет отдельного materialized read-model/дашборда по аудит-метрикам за периоды.

## 4. GAP к целевой архитектуре

1. Поднять FastMCP сервисы по контрактам blueprint (`Retrieval MCP`, `Repository MCP`, `Artifact Writer MCP`).
2. Ввести async/queue execution для long-running задач и retry-политику.
3. Собрать production deployment-профиль для Ubuntu 24: конфигурации, секреты, мониторинг, runbook.
4. Развить ingestion/template/authoring/assembly workflows.
5. Добавить observability/metrics/audit dashboards и периодические агрегаты по `task_events`.

## 5. План следующего инкремента

1. Подготовить первый FastMCP runtime сервис (`Retrieval MCP`) на FastMCP.
2. Зафиксировать deployment smoke/runbook для Ubuntu 24 c `stage`/`prod` профилями.
3. Расширить reference-case `saa_release_readiness` шагом authoring + traceability.
4. Добавить периодические агрегаты аудита (`day/week`) и API чтения этих метрик.
5. Добавить интеграционные тесты для расширенного audit read-model.
