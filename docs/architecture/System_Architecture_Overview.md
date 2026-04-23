# System Architecture Overview

Дата обновления: 2026-04-23
Статус: Increment 25

## 1. Целевой архитектурный ориентир

Система строится по модели из `./docs`:

- LangGraph как единый orchestration runtime;
- OOP framework layer с типизированными контрактами;
- domain-пакеты поверх framework-абстракций;
- infra adapters с изоляцией concrete интеграций;
- FastAPI + FastMCP на сервисных границах;
- PostgreSQL + pgvector для состояния, метаданных и векторов.

## 2. Текущая реализация (Increment 25)

Реализовано:

- framework и schemas layer;
- root roadmap `BACKLOG.md` для завершения backend/framework части;
- framework extension guide `docs/framework_extension_guide.md`;
- contract tests для базовых framework agents/tools/mcp/db/stores;
- Knowledge Factory MVP:
  - canonical document contracts в `schemas.documents`;
  - `domain_docs` package;
  - `CanonicalDocumentParser` для `.md/.txt/.json/.docx/.pdf`;
  - `KnowledgeIndexingWorkflow`;
  - `CanonicalDocumentApplicationService`;
  - `PostgresCanonicalDocumentStore`;
  - smoke `backend/scripts/smoke_knowledge_indexing.sh/.ps1`;
- canonical retrieval source:
  - `task_context.knowledge_source=canonical`;
  - `task_context.canonical_doc_ids`;
  - loader `load_canonical_knowledge_dataset`;
  - `CanonicalVectorRetriever`;
  - embedding write path в `app.embeddings`;
  - smoke `backend/scripts/smoke_canonical_retrieval.sh/.ps1`.
- `BaseWorkflow` с LangGraph-backed compile/invoke/resume;
- API boundary + task lifecycle + interrupt/resume ветки;
- persistence adapters:
  - `PostgresDocumentRepository`;
  - `PostgresArtifactStore`;
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
  - `backend/migrations/0005_task_events_status_filter_indexes.sql`;
  - `backend/migrations/0006_artifact_store.sql`;
  - `backend/migrations/0007_task_artifacts.sql`;
  - `backend/migrations/0008_hitl_actions.sql`;
  - `backend/migrations/0009_canonical_knowledge_store.sql`.
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
- authoring API:
  - `POST /api/v1/tasks/authoring/start`;
  - `POST /api/v1/tasks/authoring/start_async`;
  - `GET /api/v1/tasks/{task_id}/artifact`;
  - `GET /api/v1/tasks/{task_id}/hitl`;
  - `POST /api/v1/tasks/{task_id}/hitl/submit`;
  - `GET /api/v1/hitl/actions`;
  - traceability payload: `retrieval_task_id`, `source_refs`, `sections`;
  - `draft_strategy`: `auto|deterministic|llm`;
  - `workflow_mode`: `single_pass|multi_step`;
  - `hitl_required`: bool.
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
- file-based demo pipeline для release readiness:
  - входной markdown `release_packet.md` -> генерация retrieval dataset JSON;
  - запуск retrieval через `case_dataset_path`;
  - генерация итогового markdown-отчета `release_readiness_report.md` с GO/NO-GO интерпретацией.
- multi-file ingestion для retrieval:
  - поддержка `task_context.case_dataset_dir`;
  - ingestion директории с файлами `.md/.txt/.json` в summary/detail блоки;
  - новый demo-кейс `release_go_no_go_multifile_case`.
- Retrieval MCP MVP:
  - app entrypoint `apps/mcp_retrieval/main.py`;
  - сервис `FastMcpRetrievalService`;
  - минимальный MCP tool `build_evidence_pack`.
- Repository MCP MVP:
  - app entrypoint `apps/mcp_repository/main.py`;
  - сервис `FastMcpRepositoryService`;
  - MCP tools: `upsert_document`, `get_document`, `list_documents`.
- Artifact Writer MCP MVP:
  - app entrypoint `apps/mcp_artifact_writer/main.py`;
  - сервис `FastMcpArtifactWriterService`;
  - MCP tools: `write_artifact`, `get_artifact`, `list_artifacts`.
- Authoring application flow:
  - `AuthoringApplicationService`;
  - orchestration `retrieval -> research -> writer -> reviewer -> assembly -> artifact`;
  - persistence link `task -> artifact` через `PostgresTaskArtifactRegistry`;
  - опциональная реальная LLM-генерация draft через OpenRouter gateway;
  - fallback в deterministic draft при недоступности LLM (если strict-mode выключен);
  - steps read-model в task details и artifact metadata (`steps_summary`);
  - поддержан статус паузы `waiting_human` и возобновление по `hitl/submit`.
- async execution контур:
  - Celery worker app: `apps/worker/celery_app.py` + `apps/worker/tasks.py`;
  - dispatcher policy: `APP_ASYNC_PROVIDER=inline|celery`;
  - docker deployment для очереди: `backend/docker-compose.async.yml` (`redis` + `celery-worker`);
  - operational scripts: `backend/scripts/async_up/down.sh(.ps1)`.
- iterative HITL контур:
  - `hitl/submit` поддерживает `idempotency_key` и `expected_iteration`;
  - continuation после submit исполняется через async dispatcher (`enqueue_hitl_action`);
  - worker task `run_authoring_hitl_action` обрабатывает approve/reject/needs_changes;
  - `needs_changes` запускает rewrite + reviewer rerun и переводит задачу в новую итерацию `waiting_human`;
  - введены лимиты итераций и SLA-дедлайн (`APP_HITL_MAX_ITERATIONS`, `APP_HITL_WAIT_TIMEOUT_SEC`).
- HITL persistence/read-model:
  - отдельный adapter `PostgresHitlActionStore`;
  - reviewer действия сохраняются в таблицу `app.hitl_actions`;
  - history API `GET /api/v1/hitl/actions` поддерживает фильтры `task_id/decision/status/reviewer/from/to` и cursor pagination.
- document application layer:
  - `DocumentApplicationService` для операций repository домена;
  - list-операция в `PostgresDocumentRepository` (`limit/offset`) для MCP read-model.
- artifact application layer:
  - `ArtifactApplicationService` для операций artifact store;
  - list-операция в `PostgresArtifactStore` (`limit/offset`, фильтр `artifact_type`).
- усилена операционная стабильность smoke/demo:
  - приоритет `./.venv` интерпретатора в `.sh/.ps1` скриптах;
  - явная проверка `uvicorn` до запуска API в smoke-скриптах.
- добавлены MCP scripts для repository контура:
  - `backend/scripts/run_repository_mcp.sh/.ps1`;
  - `backend/scripts/smoke_repository_mcp.sh/.ps1` + `smoke_repository_mcp.py`.
- добавлены MCP scripts для artifact writer контура:
  - `backend/scripts/run_artifact_writer_mcp.sh/.ps1`;
  - `backend/scripts/smoke_artifact_writer_mcp.sh/.ps1` + `smoke_artifact_writer_mcp.py`.
- добавлены authoring API scripts:
  - `backend/scripts/smoke_authoring_api.sh/.ps1` + `smoke_authoring_api.py`;
  - `backend/scripts/demo_release_authoring_traceability_case.sh/.ps1`.
- добавлены async authoring scripts:
  - `backend/scripts/smoke_authoring_async_api.sh/.ps1` + `smoke_authoring_async_api.py`;
  - `backend/scripts/demo_release_authoring_async_hitl_case.sh/.ps1`.
- тестовое покрытие:
  - unit + integration + e2e;
  - e2e с реальным PostgreSQL: `test_fastapi_retrieval_e2e_postgres.py`;
  - e2e покрытие старта задачи с `case_dataset_path`;
  - e2e покрытие старта задачи с `case_dataset_dir`;
  - внешний integration test с real LLM:
    - `backend/tests/integration/test_authoring_openrouter_external.py` (флаг `RUN_EXTERNAL_LLM_TESTS=1`);
  - smoke сценарий: `backend/scripts/smoke_retrieval_api.sh`.
- архитектурные решения:
  - `docs/adr/0017-dedicated-langgraph-checkpoint-storage.md`;
  - `docs/adr/0018-task-events-status-filters-and-summary-read-model.md`;
  - `docs/adr/0019-file-based-demo-release-go-no-go-pipeline.md`;
  - `docs/adr/0020-multifile-ingestion-and-retrieval-mcp-mvp.md`;
  - `docs/adr/0021-repository-mcp-mvp-and-document-tools.md`;
  - `docs/adr/0022-artifact-writer-mcp-mvp-and-postgres-artifact-store.md`;
  - `docs/adr/0023-authoring-api-flow-and-task-artifact-traceability-link.md`;
  - `docs/adr/0024-openrouter-llm-authoring-draft-gateway.md`;
  - `docs/adr/0025-multistep-authoring-workflow-and-section-traceability.md`;
  - `docs/adr/0026-celery-redis-async-authoring-and-hitl-mvp.md`.
  - `docs/adr/0027-iterative-hitl-loop-and-async-submit-continuation.md`.
  - `docs/adr/0028-hitl-actions-persistence-and-read-model-api.md`.
  - `docs/adr/0029-framework-hardening-and-extension-guide.md`.
  - `docs/adr/0030-canonical-document-parsing-and-indexing-mvp.md`.
  - `docs/adr/0031-canonical-document-store-and-binary-parser-adapters.md`.
  - `docs/adr/0032-canonical-knowledge-retrieval-source.md`.
  - `docs/adr/0033-knowledge-block-embedding-index-and-vector-retrieval.md`.

## 3. Архитектурные ограничения текущей версии

- MCP-контур включает Retrieval/Repository/Artifact Writer MCP, но пока без unified auth/rate-limit/observability политик;
- HITL now iterative с persistence/read-model API, но нет reviewer UI/queue dashboard и агрегатов/дашбордов по reviewer действиям за периоды;
- отсутствуют полноценные `domain_authoring` workflows;
- `domain_docs` поддерживает базовые `.docx/.pdf` parser adapters и отдельный knowledge block persistence, но OCR/rich layout/table extraction еще не реализованы;
- async контур есть только для authoring (остальные long-running задачи пока в sync path);
- нет полноценного production deployment runbook с эксплуатационными SLO/SLI метриками;
- нет отдельного materialized read-model/дашборда по аудит-метрикам за периоды.

## 4. GAP к целевой архитектуре

1. Дорастить MCP-контур: унификация контрактов и операционных политик между Retrieval/Repository/Artifact Writer сервисами.
2. Дорастить async execution до общего execution-plane (не только authoring).
3. Дорастить ingestion до OCR/rich layout/table extraction и quality gates.
4. Добавить агрегаты и аналитические read-model поверх reviewer действий (SLA, decisions, reviewer load).
5. Добавить observability/metrics/audit dashboards и периодические агрегаты по `task_events`.

## 5. План следующего инкремента

1. Добавить quality gates для пустых/слабо структурированных документов.
2. Расширить release go/no-go demo входами через canonical ingestion.
3. Добавить OCR/table/rich layout extraction как отдельный parser sub-slice.
4. Подготовить Retrieval MCP tools для canonical source lookup.
5. Заменить deterministic embedding stub на real TEI HTTP client.
