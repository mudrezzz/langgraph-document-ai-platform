# Framework Concepts

Update date: 2026-04-30
Status: Active (P0 concept guide)

The document gives a working mental model of the framework layer: how the layers are arranged, how execution goes in runtime and where the expansion points are located.

## 1. Layer map (what is responsible for what)

Source: `backend/packages/*`, `backend/apps/*`.

- `schemas/*`:
- public typed contracts for API/MCP/workflow/document/authoring.
- This is the main layer of payload compatibility.
- `framework/*`:
  - reusable primitives (`BaseWorkflow`, `ToolExecutor`, `BaseFastMcpService`, RBAC policy, stores interfaces).
- sets execution contracts and extension hooks.
- `application/*`:
- orchestration of business scenarios in the task lifecycle (`retrieval`, `knowledge_indexing`, `authoring`, `hitl`, `observability`).
- connects framework + domain + infra adapters.
- `domain_*/*`:
- domain pipeline/policies (`domain_rag`, `domain_docs`, `domain_authoring`).
- should not bypass the task lifecycle directly.
- `infra/*`:
- specific PostgreSQL/pgvector/TEI/OpenRouter/FastMCP/OCR adapters.
- `apps/*`:
- external service boundaries: FastAPI (`apps/api`) and FastMCP (`apps/mcp_*`), async worker (`apps/worker`).

## 2. Runtime execution model

Key contract: `backend/packages/framework/workflows/base.py`.

- `BaseWorkflow.compile()`:
- builds invoke/resume graph from `workflow_nodes(is_resume=...)`.
- when LangGraph is available, the `runtime_mode=langgraph` mode is launched.
- without LangGraph, fallback runtime with the same node-hook API is used.
- `BaseWorkflow.invoke(payload)`:
- validates payload via `state_schema()`;
- executes the invoke branch of the graph.
- `BaseWorkflow.resume(payload)`:
- executes the resume branch (checkpoint/interrupt continuation).
- `task_context.task_id`:
- used as `thread_id` for LangGraph checkpointer (`_resolve_thread_id`).
- this is the basis of a stable interrupt/resume for long-running tasks.
- `WorkflowNodeEventSink`:
- node events `started/completed/failed` are issued from `BaseWorkflow`;
- in the application they map to task audit read-model.

## 3. Task lifecycle model (API-level)

Source: `backend/packages/application/task_service.py`, `backend/apps/api/main.py`.

- Basic statuses:
  - `queued`, `running`, `waiting_human`, `completed`, `failed`.
- Main flow:
  - `create_task -> update_task(running) -> complete_task|fail_task`.
- Audit/read-model:
  - `GET /api/v1/tasks`
  - `GET /api/v1/tasks/events`
  - `GET /api/v1/tasks/events/summary`
  - `GET /api/v1/tasks/observability/summary`
- `details` stores execution metadata:
  - `execution_mode`, `dispatch_id`, `queue_name`, `queued_at`, `started_at`, `completed_at|failed_at`, `queue_wait_ms`, `duration_ms`.

## 4. Async plane model

Source: `backend/apps/api/dependencies.py`, `backend/packages/application/*service.py`, `backend/apps/worker/celery_app.py`.

- Switching execution plane:
  - `APP_ASYNC_PROVIDER=inline|celery`.
- For async start endpoints:
- task is created in `queued`;
- payload is placed in the dispatcher queue;
- worker executes `run_existing_task(...)`.
- Queues:
  - `authoring`: `APP_CELERY_QUEUE`
  - `knowledge-indexing`: `APP_CELERY_INDEXING_QUEUE`
  - `retrieval`: `APP_CELERY_RETRIEVAL_QUEUE`

## 5. HITL model

Source: `backend/packages/application/authoring_service.py`, `backend/apps/api/main.py`.

- HITL endpoints:
  - `GET /api/v1/tasks/{task_id}/hitl`
  - `POST /api/v1/tasks/{task_id}/hitl/submit`
  - `GET /api/v1/hitl/actions`
  - `GET /api/v1/hitl/observability/summary`
- If `hitl_required=true`, authoring can go to `waiting_human`.
- Submit path accepts the reviewer decision (`approve|needs_changes|reject`) and continues the pipeline through the dispatcher plane.
- For iteration, `idempotency_key` and `expected_iteration` are used.

## 6. Quality gate model

Source: `backend/packages/application/retrieval_service.py`, `backend/packages/domain_docs/indexing/quality_policy.py`, `backend/packages/application/knowledge_indexing_service.py`.

- Retrieval quality gate:
- `quality_gate_status` is derived from `unresolved_gaps`.
- the status is usually `passed|warning|failed` in task details.
- Knowledge indexing quality policy:
- `KnowledgeIndexingQualityPolicy` gives per-document decision (`accepted/rejected`) and aggregate gate summary.
- policy is controlled by the env contract `APP_INDEXING_QUALITY_*`.
- rejected documents should not be included in canonical persistence/indexed corpus.

## 7. Security/RBAC boundary

Source: `backend/apps/api/security.py`, `backend/packages/framework/mcp/service.py`.

- Single flag: `APP_AUTH_ENABLED`.
- API path:
- actor identity via headers `X-Actor-Id`, `X-Actor-Roles`.
- sensitive endpoints require role checks (`template_admin`, `reviewer`).
- MCP path:
- sensitive tools accept `actor` + `roles` in payload.
- `BaseFastMcpService` centralize authorize + operation scopes (`read|write|action`).

## 8. Where to expand and where not to touch

- Expand:
- `domain_*` and `application` orchestration through existing contracts.
- new API/MCP surfaces via `schemas` + `apps` + docs backlog update.
- Not considered a public contract:
- internal details of `framework/*`, `application/*`, `infra/*` classes.
- direct SQL-table internals without separate policy fixation.

Before changing public behavior, check with `docs/developer_guide/public_contract_surface.md`.
