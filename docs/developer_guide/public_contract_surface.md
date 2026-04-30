# Public Contract Surface v1

Дата обновления: 2026-04-30  
Статус: Active (Increment 32 baseline)

Документ фиксирует границы стабильности framework-слоя для внешнего разработчика.

## 1. Уровни стабильности

- `Stable`: поддерживаемый публичный контракт для интеграции и расширения.
- `Experimental`: доступно для использования, но допускает несовместимые изменения между инкрементами.
- `Internal`: внутренняя реализация, не является внешним контрактом.

Assumption: для `Stable` в v1 сохраняются endpoint/tool names и базовые payload-модели из `schemas`; внутренние поля `details/metadata` могут расширяться.

## 2. Stable: HTTP API surface

Источник истины: `backend/apps/api/main.py`, `backend/packages/schemas/api/contracts.py`.

- `GET /health`
- Template Library API:
  - `PUT /api/v1/templates/{template_id}` (`template_admin`)
  - `GET /api/v1/templates/{template_id}`
  - `POST /api/v1/templates/{template_id}/publish` (`template_admin`)
  - `POST /api/v1/templates/{template_id}/status` (`template_admin`)
  - `GET /api/v1/templates`
- Task API:
  - `POST /api/v1/tasks/retrieval/start`
  - `POST /api/v1/tasks/retrieval/start_async`
  - `POST /api/v1/tasks/knowledge-indexing/start`
  - `POST /api/v1/tasks/knowledge-indexing/start_async`
  - `POST /api/v1/tasks/authoring/start`
  - `POST /api/v1/tasks/authoring/start_async`
  - `POST /api/v1/tasks/{task_id}/resume`
  - `GET /api/v1/tasks`
  - `GET /api/v1/tasks/{task_id}`
  - `GET /api/v1/tasks/{task_id}/evidence`
  - `GET /api/v1/tasks/{task_id}/artifact`
  - `GET /api/v1/tasks/events`
  - `GET /api/v1/tasks/events/summary`
  - `GET /api/v1/tasks/observability/summary`
- HITL API:
  - `GET /api/v1/tasks/{task_id}/hitl`
  - `POST /api/v1/tasks/{task_id}/hitl/submit` (`reviewer`)
  - `GET /api/v1/hitl/actions`
  - `GET /api/v1/hitl/observability/summary`

## 3. Stable: MCP service surface

Источник истины: `backend/packages/infra/fastmcp/*_service.py`, `backend/packages/schemas/mcp/*`.

- `retrieval-mcp`:
  - `build_evidence_pack` (operation scope: `action`)
  - `search_summaries` (`read`)
  - `search_blocks` (`read`)
  - `lookup_source` (`read`)
- `repository-mcp`:
  - `upsert_document` (`write`, role: `repository_writer`)
  - `get_document` (`read`)
  - `list_documents` (`read`)
- `artifact-writer-mcp`:
  - `write_artifact` (`write`, role: `artifact_writer`)
  - `get_artifact` (`read`)
  - `list_artifacts` (`read`)
- `template-library-mcp`:
  - `upsert_template` (`write`, role: `template_admin`)
  - `publish_template` (`write`, role: `template_admin`)
  - `set_template_status` (`write`, role: `template_admin`)
  - `get_template` (`read`)
  - `list_templates` (`read`)
- `review-approval-mcp`:
  - `get_hitl_status` (`read`)
  - `list_hitl_actions` (`read`)
  - `submit_hitl_review` (`write`, role: `reviewer`)
  - `get_hitl_observability_summary` (`read`)
- `configuration-library-mcp`:
  - `upsert_config` (`write`, role: `config_admin`)
  - `get_config` (`read`)
  - `list_configs` (`read`)
  - `find_similar_configs` (`read`)
  - `compare_configs` (`read`)

## 4. Stable: schema modules for integration

- HTTP/API payloads: `backend/packages/schemas/api/contracts.py`
- MCP payloads: `backend/packages/schemas/mcp/*.py`
- Retrieval contracts: `backend/packages/schemas/rag/contracts.py`
- Canonical documents: `backend/packages/schemas/documents/contracts.py`
- Authoring/HITL contracts: `backend/packages/schemas/authoring/contracts.py`, `backend/packages/schemas/approvals/contracts.py`

## 5. Stable: runtime config keys

Источник истины: `backend/apps/api/dependencies.py`, `backend/apps/api/security.py`, `backend/packages/infra/postgres/config.py`, `backend/apps/worker/celery_app.py`.

- Core runtime:
  - `APP_RUNTIME_PROFILE=dev|stage|prod`
  - `APP_DB_DSN`
  - `APP_DB_SCHEMA`
  - `APP_VECTOR_DIM`
- Auth/RBAC:
  - `APP_AUTH_ENABLED`
  - API headers: `X-Actor-Id`, `X-Actor-Roles`
  - MCP payload fields: `actor`, `roles` (для write/sensitive tools)
- Async execution plane:
  - `APP_ASYNC_PROVIDER=inline|celery`
  - `APP_CELERY_BROKER_URL`
  - `APP_CELERY_RESULT_BACKEND`
  - `APP_CELERY_QUEUE`
  - `APP_CELERY_INDEXING_QUEUE`
  - `APP_CELERY_RETRIEVAL_QUEUE`
- LLM authoring path:
  - `APP_LLM_ENABLED`
  - `APP_LLM_STRICT`
  - `APP_LLM_PROVIDER`
  - `OPENROUTER_API_KEY`
  - `OPENROUTER_MODEL`
  - `OPENROUTER_BASE_URL`

## 6. Experimental surface (v1)

- Внутреннее наполнение `details` в `TaskStatusResponse` и related observability payload fields.
- Parser-quality diagnostics и quality flags в canonical indexing/reporting (`parser_quality`, `quality_flags`).
- Retrieval source-provenance детализация для PDF/table/layout metadata (`layout_kind`, `bbox`, `reading_order_index`).
- Deterministic similarity internals в `configuration-library-mcp` (`find_similar_configs` scoring model).
- OCR provider behavior (`sidecar`/`ocrmypdf`) и связанные quality-поля.

## 7. Internal (не внешний контракт)

- Пакеты `backend/packages/framework/*`, `backend/packages/application/*`, `backend/packages/infra/*` как Python-API для прямого импорта.
- Внутренние структуры task registry/checkpoint persistence таблиц как расширяемая реализация.
- Реализация release gate orchestration в Python-скриптах (при стабильности CLI-входов скриптов).

## 8. Изменение contract surface

При изменении любого пункта из разделов `Stable`:

1. Сначала обновить этот файл.
2. Затем обновить `docs/DOCS_BACKLOG.md` (статус/notes/date).
3. Добавить ссылку на изменение в `README.md` и/или `docs/developer_guide/README.md` при изменении маршрута чтения.
