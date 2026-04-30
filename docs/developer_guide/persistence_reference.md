# Persistence & Data Reference

Дата обновления: 2026-04-30  
Статус: Active (P1 reference)

Источник истины: `backend/migrations/*.sql`, `backend/packages/infra/postgres/*`, `backend/packages/application/*`.

## 1. Runtime policy

- Основной persistence target: PostgreSQL (`APP_DB_DSN`).
- Профили:
  - `APP_RUNTIME_PROFILE=dev|stage`: fallback persistence разрешен при отсутствии DSN.
  - `APP_RUNTIME_PROFILE=prod`: fallback отключен; DSN обязателен.
- Базовый schema: `APP_DB_SCHEMA` (default `app`).

## 2. Migration policy

Применение миграций:

```bash
APP_DB_DSN=postgresql://... python backend/scripts/apply_migrations.py
```

Что важно:

- миграции выполняются в лексикографическом порядке `0001...0013`;
- migration-tracking table не используется;
- миграции проектируются idempotent (`IF NOT EXISTS`, additive `ALTER`/`CREATE INDEX IF NOT EXISTS`).

## 3. Data model map

## 3.1 Core runtime tables

- `app.documents`: generic document repository payload.
- `app.checkpoints`: task-level checkpoint payload (`run_id`, `payload`).
- `app.embeddings`: vector storage (`vector_key`, `embedding`, `metadata`).

## 3.2 Task lifecycle & observability

- `app.tasks`: latest task state (`task_id`, `task_type`, `status`, `current_node`, `details`).
- `app.task_events`: статусные события и node-level audit payload.
- Индексы фильтров/summary:
  - `ix_tasks_updated_at_task_id`
  - `ix_task_events_from_status`
  - `ix_task_events_from_to_created_at`

## 3.3 LangGraph checkpoint runtime

- `app.langgraph_checkpoints`
- `app.langgraph_checkpoint_blobs`
- `app.langgraph_checkpoint_writes`

Поддерживаемые runtime операции checkpointer:

- read/list/put checkpoint tuples
- pending writes
- `delete_thread`, `copy_thread`, `prune(strategy=keep_latest|delete)`

## 3.4 Authoring/HITL persistence

- `app.artifacts`: persisted artifacts.
- `app.task_artifacts`: traceability link `authoring task -> artifact -> retrieval_task`.
- `app.hitl_actions`: reviewer actions (`iteration`, `decision`, `status`, `idempotency_key`, `metadata`).

## 3.5 Knowledge Factory (canonical)

Latest read-model:

- `app.canonical_documents`
- `app.knowledge_blocks`

Version history:

- `app.canonical_document_versions`
- `app.knowledge_block_versions`

Policy:

- latest lookup по `doc_id` читает `canonical_documents`;
- explicit version lookup (`doc_id + version`) читает `canonical_document_versions`;
- при re-index latest layer обновляется, исторические версии сохраняются.

## 3.6 Template & configuration libraries

- `app.document_templates`:
  - PK `(template_id, version)`;
  - lifecycle status `draft|published|deprecated|archived`.
- `app.configuration_library`:
  - PK `(config_id, version)`;
  - JSONB payload/metadata/tags + type/tag filters.

## 4. Version lookup contracts

Canonical document path (`CanonicalDocumentApplicationService`):

- `get_document(doc_id)` -> latest version.
- `get_document(doc_id, version=...)` -> explicit historical version.
- `list_versions(doc_id)` -> ordered version history with `is_latest`.
- `list_blocks(..., version=None)` -> latest blocks.
- `list_blocks(..., version=...)` -> version-specific blocks.

## 5. Cursor and ordering contracts

Task/history read models:

- `tasks`: `ORDER BY updated_at DESC, task_id DESC`
- `task_events`: `ORDER BY created_at DESC, event_id DESC`
- cursors кодируются/декодируются в application layer и считаются частью API behavior.

HITL actions:

- `ORDER BY created_at DESC, action_id DESC`
- cursor-based pagination через `action_id + created_at`.

## 6. Rollback expectations

Текущая стратегия:

- schema migrations additive; destructive rollback SQL не поддерживается как стандартный путь;
- rollback на проде предполагает:
  - восстановление из backup;
  - или forward-fix migration.

Практический контракт для изменений:

1. Не удалять существующие таблицы/колонки, используемые public read-model endpoint-ами.
2. Не ломать latest/history compatibility для canonical и templates/config versions.
3. Для каждого schema-change обновлять docs + backlog.

## 7. Operational checks

Минимум после migration/data change:

1. `bash backend/scripts/postgres_migrate.sh`
2. `bash backend/scripts/smoke_retrieval_api.sh`
3. `bash backend/scripts/smoke_knowledge_indexing_api.sh --build-binary-demo-docs`
4. `bash backend/scripts/smoke_authoring_api.sh`
5. `bash backend/scripts/smoke_release_gate.sh --gate-profile stage`

## 8. Связанные документы

- `docs/developer_guide/env_config_reference.md`
- `docs/developer_guide/api_reference.md`
- `docs/production_runbook.md`
