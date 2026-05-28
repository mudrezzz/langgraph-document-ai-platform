# Public Contract Surface v1

Update date: 2026-04-30
Status: Active (Increment 32 baseline)

The document fixes the boundaries of stability of the framework layer for an external developer.

## 1. Stability levels

- `Stable`: supported public contract for integration and extension.
- `Experimental`: Available for use, but allows inconsistent changes between increments.
- `Internal`: internal implementation, not an external contract.

Assumption: for `Stable` in v1 the endpoint/tool ​​names and basic payload models from `schemas` are saved; `details/metadata` internal fields can be expanded.

## 2. Stable: HTTP API surface

Source of truth: `backend/apps/api/main.py`, `backend/packages/schemas/api/contracts.py`.

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

Source of truth: `backend/packages/infra/fastmcp/*_service.py`, `backend/packages/schemas/mcp/*`.

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

Source of truth: `backend/apps/api/dependencies.py`, `backend/apps/api/security.py`, `backend/packages/infra/postgres/config.py`, `backend/apps/worker/celery_app.py`.

- Core runtime:
  - `APP_RUNTIME_PROFILE=dev|stage|prod`
  - `APP_DB_DSN`
  - `APP_DB_SCHEMA`
  - `APP_VECTOR_DIM`
- Auth/RBAC:
  - `APP_AUTH_ENABLED`
  - API headers: `X-Actor-Id`, `X-Actor-Roles`
- MCP payload fields: `actor`, `roles` (for write/sensitive tools)
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

- Internal content of `details` in `TaskStatusResponse` and related observability payload fields.
- Parser-quality diagnostics and quality flags in canonical indexing/reporting (`parser_quality`, `quality_flags`).
- Retrieval source-provenance detailing for PDF/table/layout metadata (`layout_kind`, `bbox`, `reading_order_index`).
- Deterministic similarity internals in `configuration-library-mcp` (`find_similar_configs` scoring model).
- OCR provider behavior (`sidecar`/`ocrmypdf`) and related quality fields.

## 7. Internal (not an external contract)

- Packages `backend/packages/framework/*`, `backend/packages/application/*`, `backend/packages/infra/*` as Python API for direct import.
- Internal structures of task registry/checkpoint persistence tables as an extensible implementation.
- Implementation of release gate orchestration in Python scripts (with stability of CLI script inputs).

## 8. Changing the contract surface

When changing any item from sections `Stable`:

1. First update this file.
2. Then update `docs/DOCS_BACKLOG.md` (status/notes/date).
3. Add a change link to `README.md` and/or `docs/developer_guide/README.md` when changing the reading route.
