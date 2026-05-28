# API Reference (FastAPI)

Update date: 2026-04-30
Status: Active (P0 reference)

Source of truth: `backend/apps/api/main.py`, `backend/packages/schemas/api/contracts.py`.

## 1. Health

- `GET /health`
- Response: `{"status":"ok"}`

## 2. Template Library API

- `PUT /api/v1/templates/{template_id}`
  - Body: `UpsertTemplateRequest`
  - Response: `TemplateResponse`
  - Auth: role `template_admin` (when `APP_AUTH_ENABLED=true`)
- `GET /api/v1/templates/{template_id}`
  - Query: `version` (optional)
  - Response: `TemplateResponse`
- `POST /api/v1/templates/{template_id}/publish`
  - Body: `PublishTemplateRequest`
  - Response: `TemplateResponse`
  - Auth: role `template_admin`
- `POST /api/v1/templates/{template_id}/status`
  - Body: `SetTemplateStatusRequest`
  - Response: `TemplateResponse`
  - Auth: role `template_admin`
- `GET /api/v1/templates`
  - Query: `limit`, `offset`, `template_id`, `status`
  - Response: `TemplateListResponse`

## 3. Retrieval tasks API

- `POST /api/v1/tasks/retrieval/start`
  - Body: `StartRetrievalTaskRequest`
  - Response: `StartTaskResponse`
- `POST /api/v1/tasks/retrieval/start_async`
  - Body: `StartRetrievalTaskRequest`
  - Response: `StartTaskResponse` (`status=queued` expected for async path)

## 4. Knowledge Indexing API

- `POST /api/v1/tasks/knowledge-indexing/start`
  - Body: `StartKnowledgeIndexingTaskRequest`
  - Response: `StartTaskResponse`
- `POST /api/v1/tasks/knowledge-indexing/start_async`
  - Body: `StartKnowledgeIndexingTaskRequest`
  - Response: `StartTaskResponse`

## 5. Authoring + HITL API

- `POST /api/v1/tasks/authoring/start`
  - Body: `StartAuthoringTaskRequest`
  - Response: `StartTaskResponse`
- `POST /api/v1/tasks/authoring/start_async`
  - Body: `StartAuthoringTaskRequest`
  - Response: `StartTaskResponse`
- `GET /api/v1/tasks/{task_id}/artifact`
  - Response: `TaskArtifactResponse`
- `GET /api/v1/tasks/{task_id}/hitl`
  - Response: `HitlReviewStatusResponse`
- `POST /api/v1/tasks/{task_id}/hitl/submit`
  - Body: `SubmitHitlReviewRequest`
  - Response: `TaskStatusResponse`
  - Auth: role `reviewer`
- `GET /api/v1/hitl/actions`
  - Query: `limit`, `cursor`, `task_id`, `decision`, `status`, `reviewer`, `from`, `to`
  - Response: `HitlActionsResponse`
- `GET /api/v1/hitl/observability/summary`
  - Query: `task_id`, `decision`, `status`, `reviewer`, `from`, `to`
  - Response: `HitlObservabilityResponse`

## 6. Task lifecycle/read-model API

- `GET /api/v1/tasks`
  - Query: `limit`, `cursor`, `status`, `task_type`, `from`, `to`
  - Response: `TaskHistoryResponse`
- `GET /api/v1/tasks/{task_id}`
  - Response: `TaskStatusResponse`
- `GET /api/v1/tasks/{task_id}/evidence`
  - Response: `EvidencePackResponse`
- `GET /api/v1/tasks/events`
  - Query: `limit`, `cursor`, `task_id`, `task_type`, `from_status`, `to_status`, `from`, `to`
  - Response: `TaskEventsResponse`
- `GET /api/v1/tasks/events/summary`
  - Query: `task_id`, `task_type`, `from_status`, `to_status`, `from`, `to`
  - Response: `TaskEventsSummaryResponse`
- `GET /api/v1/tasks/observability/summary`
  - Query: `status`, `task_type`, `from`, `to`
  - Response: `TaskObservabilityResponse`
- `POST /api/v1/tasks/{task_id}/resume`
  - Body: `ResumeTaskRequest`
  - Response: `TaskStatusResponse`

## 7. Error mapping

- `400 Bad Request`:
  - invalid cursor
  - workflow execution error
- `401 Unauthorized`:
- no actor identity when `APP_AUTH_ENABLED` and required role are enabled
- `403 Forbidden`:
- actor without the required role
- `404 Not Found`:
- task/template/artifact/link not found
- `409 Conflict`:
  - invalid task state
  - invalid template status transition

## 8. Auth headers (API boundary)

With `APP_AUTH_ENABLED=true` for protected endpoints the following is used:

- `X-Actor-Id`
- `X-Actor-Roles` (comma-separated roles)

## 9. Related documents

- `docs/developer_guide/public_contract_surface.md`
- `docs/developer_guide/framework_concepts.md`
- `docs/developer_guide/canonical_e2e_walkthrough.md`
