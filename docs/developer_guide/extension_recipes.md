# Extension Recipes

The document shows a practical pattern for extending a library without breaking existing public contracts.

## 1. Adding a new workflow

1. Add state schema to `backend/packages/schemas/workflow` or domain `schemas` module.
2. Implement workflow on `framework.workflows.BaseWorkflow`.
3. For multi-node scenario use `workflow_nodes(is_resume=...)` and `WorkflowNodeSpec`.
4. Throw `task_context.task_id` and `task_context.correlation_id` for audit/checkpoint consistency.
5. Register the workflow via application service or `WorkflowFactory.register_builder(...)`.
6. Add invoke/resume/error + node events tests.

See basic rules: `docs/framework_extension_guide.md`.

## 2. Adding a new tool

1. Describe typed input/output contracts.
2. Implement `framework.tools.BaseTool`.
3. Register with `ToolRegistry`.
4. Call via `ToolExecutor` from `ToolExecutionPolicy`.
5. Add audit sink if you need a task-level trace.
6. Cover retry/idempotency/failure contract tests.

## 3. Adding a new MCP boundary

1. Add MCP schemas to `backend/packages/schemas/mcp`.
2. Implement the service from `framework.mcp.BaseFastMcpService`.
3. Connect `_register_toolset(...)` and `_authorize_tool(...)` for sensitive operations.
4. Add `backend/apps/mcp_<name>/main.py` entrypoint.
5. Add `run_*.sh/.ps1` and `smoke_*.sh/.ps1`.
6. Add unit/integration tests for direct service calls and script contracts.

## 4. Adding a persistence adapter

1. Define Protocol/contract in the framework/application layer.
2. Implement adapter in `backend/packages/infra`.
3. Add additive migration to `backend/migrations`.
4. If there is a latest/history split, keep the backward-compatible latest read contract.
5. Cover tests on mapping, latest/history lookup and cursors.

## 5. Minimum quality gate for each extension slice

1. Targeted tests on the changed domain.
2. Full gate:

```bash
OPENROUTER_API_KEY="$(awk -F= '/^OPENROUTER_API_KEY=/{print substr($0, index($0,"=")+1)}' backend/.env)" \
OPENROUTER_MODEL="$(awk -F= '/^OPENROUTER_MODEL=/{print substr($0, index($0,"=")+1)}' backend/.env)" \
OPENROUTER_BASE_URL="$(awk -F= '/^OPENROUTER_BASE_URL=/{print substr($0, index($0,"=")+1)}' backend/.env)" \
RUN_DOCKER_ASYNC_E2E=1 RUN_EXTERNAL_LLM_TESTS=1 \
.venv/bin/pytest backend/tests -rs
```
