# Framework Concepts

Дата обновления: 2026-04-30  
Статус: Active (P0 concept guide)

Документ дает рабочую mental model framework-слоя: как устроены слои, как идет execution в runtime и где находятся точки расширения.

## 1. Layer map (что за что отвечает)

Источник: `backend/packages/*`, `backend/apps/*`.

- `schemas/*`:
  - публичные typed contracts для API/MCP/workflow/document/authoring.
  - это основной слой payload-совместимости.
- `framework/*`:
  - reusable primitives (`BaseWorkflow`, `ToolExecutor`, `BaseFastMcpService`, RBAC policy, stores interfaces).
  - задает execution contracts и extension hooks.
- `application/*`:
  - orchestration бизнес-сценариев в task lifecycle (`retrieval`, `knowledge_indexing`, `authoring`, `hitl`, `observability`).
  - связывает framework + domain + infra adapters.
- `domain_*/*`:
  - доменные pipeline/политики (`domain_rag`, `domain_docs`, `domain_authoring`).
  - не должны обходить task lifecycle напрямую.
- `infra/*`:
  - конкретные адаптеры PostgreSQL/pgvector/TEI/OpenRouter/FastMCP/OCR.
- `apps/*`:
  - внешние сервисные границы: FastAPI (`apps/api`) и FastMCP (`apps/mcp_*`), async worker (`apps/worker`).

## 2. Runtime execution model

Ключевой контракт: `backend/packages/framework/workflows/base.py`.

- `BaseWorkflow.compile()`:
  - строит invoke/resume graph из `workflow_nodes(is_resume=...)`.
  - при доступном LangGraph запускается режим `runtime_mode=langgraph`.
  - без LangGraph используется fallback runtime с тем же node-hook API.
- `BaseWorkflow.invoke(payload)`:
  - валидирует payload через `state_schema()`;
  - исполняет invoke-ветку графа.
- `BaseWorkflow.resume(payload)`:
  - исполняет resume-ветку (checkpoint/interrupt continuation).
- `task_context.task_id`:
  - используется как `thread_id` для LangGraph checkpointer (`_resolve_thread_id`).
  - это основа устойчивого interrupt/resume для long-running задач.
- `WorkflowNodeEventSink`:
  - node events `started/completed/failed` эмитятся из `BaseWorkflow`;
  - в приложении мапятся в task audit read-model.

## 3. Task lifecycle model (API-level)

Источник: `backend/packages/application/task_service.py`, `backend/apps/api/main.py`.

- Базовые статусы:
  - `queued`, `running`, `waiting_human`, `completed`, `failed`.
- Основной flow:
  - `create_task -> update_task(running) -> complete_task|fail_task`.
- Audit/read-model:
  - `GET /api/v1/tasks`
  - `GET /api/v1/tasks/events`
  - `GET /api/v1/tasks/events/summary`
  - `GET /api/v1/tasks/observability/summary`
- В `details` сохраняются execution metadata:
  - `execution_mode`, `dispatch_id`, `queue_name`, `queued_at`, `started_at`, `completed_at|failed_at`, `queue_wait_ms`, `duration_ms`.

## 4. Async plane model

Источник: `backend/apps/api/dependencies.py`, `backend/packages/application/*service.py`, `backend/apps/worker/celery_app.py`.

- Переключение execution plane:
  - `APP_ASYNC_PROVIDER=inline|celery`.
- Для async start endpoint-ов:
  - task создается в `queued`;
  - payload ставится в dispatcher queue;
  - worker исполняет `run_existing_task(...)`.
- Очереди:
  - `authoring`: `APP_CELERY_QUEUE`
  - `knowledge-indexing`: `APP_CELERY_INDEXING_QUEUE`
  - `retrieval`: `APP_CELERY_RETRIEVAL_QUEUE`

## 5. HITL model

Источник: `backend/packages/application/authoring_service.py`, `backend/apps/api/main.py`.

- HITL endpoint-ы:
  - `GET /api/v1/tasks/{task_id}/hitl`
  - `POST /api/v1/tasks/{task_id}/hitl/submit`
  - `GET /api/v1/hitl/actions`
  - `GET /api/v1/hitl/observability/summary`
- Если `hitl_required=true`, authoring может перейти в `waiting_human`.
- Submit path принимает reviewer decision (`approve|needs_changes|reject`) и продолжает pipeline через dispatcher plane.
- Для итеративности используются `idempotency_key` и `expected_iteration`.

## 6. Quality gate model

Источник: `backend/packages/application/retrieval_service.py`, `backend/packages/domain_docs/indexing/quality_policy.py`, `backend/packages/application/knowledge_indexing_service.py`.

- Retrieval quality gate:
  - `quality_gate_status` выводится из `unresolved_gaps`.
  - статус обычно `passed|warning|failed` в task details.
- Knowledge indexing quality policy:
  - `KnowledgeIndexingQualityPolicy` дает per-document decision (`accepted/rejected`) и aggregate gate summary.
  - policy управляется env-контрактом `APP_INDEXING_QUALITY_*`.
  - rejected documents не должны попадать в canonical persistence/indexed corpus.

## 7. Security/RBAC boundary

Источник: `backend/apps/api/security.py`, `backend/packages/framework/mcp/service.py`.

- Единый флаг: `APP_AUTH_ENABLED`.
- API path:
  - actor identity через headers `X-Actor-Id`, `X-Actor-Roles`.
  - sensitive endpoint-ы требуют role checks (`template_admin`, `reviewer`).
- MCP path:
  - sensitive tools принимают `actor` + `roles` в payload.
  - `BaseFastMcpService` централизует authorize + operation scopes (`read|write|action`).

## 8. Где расширять, а где не трогать

- Расширять:
  - `domain_*` и `application` orchestration через существующие contracts.
  - новые API/MCP surfaces через `schemas` + `apps` + docs backlog update.
- Не считать публичным контрактом:
  - внутренние детали `framework/*`, `application/*`, `infra/*` классов.
  - прямые SQL-table internals без отдельной policy фиксации.

Перед изменением public behavior сверяйтесь с `docs/developer_guide/public_contract_surface.md`.
