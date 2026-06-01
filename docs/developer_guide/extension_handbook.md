# Extension Handbook

Update date: 2026-04-30
Status: Active (P0 extension set)

Goal: to provide a repeatable path for extensions based on key types of changes to the framework layer.

Basic documents:

- `docs/framework_extension_guide.md`
- `docs/developer_guide/extension_recipes.md`
- `docs/developer_guide/public_contract_surface.md`

## 1. Workflow extension playbook

When to use: new workflow/state-machine path (retrieval/authoring/indexing-like scenarios).

Minimum change set:

1. Add/update state contract:
- `backend/packages/schemas/workflow/*` (or domain `schemas`).
2. Implement workflow:
   - `backend/packages/domain_*/**/workflows.py`
- based on `framework.workflows.BaseWorkflow`.
3. Add task lifecycle orchestration:
   - `backend/packages/application/*_service.py`.
4. Connect the API endpoint (if an external contract is needed):
   - `backend/apps/api/main.py`
   - `backend/packages/schemas/api/contracts.py`.
5. Add smoke/test coverage:
   - `backend/tests/*`
   - `backend/scripts/smoke_*`.

Critical Rules:

- save `task_context.task_id` for checkpoint consistency;
- do not break `invoke/resume` compatibility;
- save node events in task audit through the existing sink path.

## 2. Tool extension playbook

When to use: new domain tool for workflow execution.

Minimum change set:

1. Implement an `BaseTool`-compatible tool (`framework.tools` contracts).
2. Register the tool in the registry/executor path.
3. Set execution policy (retry/idempotency/audit).
4. Register typed input/output models in `schemas`.
5. Add unit tests for success/retry/failure/idempotency.

Critical Rules:

- all public payloads are typed through Pydantic;
- sensitive operations must be compatible with RBAC policy.

## 3. MCP extension playbook

When to use: new MCP boundary or extension of an existing one.

Minimum change set:

1. Add MCP contracts:
   - `backend/packages/schemas/mcp/<service>.py`.
2. Implement the service:
   - `backend/packages/infra/fastmcp/<service>_service.py`
- based on `BaseFastMcpService`.
3. Register toolset with the correct scopes/roles:
   - `_register_toolset(...)`
- `_authorize_tool(...)` for write/sensitive operations.
4. Add app entrypoint:
   - `backend/apps/mcp_<service>/main.py`.
5. Add scripts:
   - `backend/scripts/run_<service>_mcp.sh/.ps1`
   - `backend/scripts/smoke_<service>_mcp.sh/.ps1/.py`.

Critical Rules:

- comply with naming/scope policy (`read|write|action`);
- errors are reported through a single operation error mapping;
- update `docs/developer_guide/mcp_reference.md`.

## 4. Persistence extension playbook

When to use: new store/read-model or extension of the current data schema.

Minimum change set:

1. Define interface/contract (framework/application layer).
2. Implement adapter in `backend/packages/infra/postgres/*`.
3. Add additive migration:
   - `backend/migrations/00xx_*.sql`.
4. Embed in DI:
   - `backend/apps/api/dependencies.py`.
5. Add tests:
   - mapping/read-model/cursor/history paths.

Critical Rules:

- additive migrations only;
- do not break latest/history read contracts;
- record new runtime effects in `env_config_reference.md` (if there are new envs).

## 5. Domain extension playbook

When to use: New business logic in `domain_docs`, `domain_rag`, `domain_authoring` or new `domain_*` module.

Minimum change set:

1. Add domain contracts/models to `schemas`.
2. Add domain services/workflows.
3. Integrate via application service (not directly into the API).
4. Add smoke/demo proof path to `backend/scripts`.
5. Update docs:
   - concept/reference/guides + `docs/DOCS_BACKLOG.md`.

Critical Rules:

- the domain should not bypass the task lifecycle;
- observability fields for new long-running paths must fall into existing summary endpoints.

## 6. Definition of done for any extension

Extension is considered complete if:

1. Contracts are typed and covered with tests.
2. There is a smoke proof path (script or API flow).
3. The corresponding docs sections have been updated.
4. Updated `docs/DOCS_BACKLOG.md`.
