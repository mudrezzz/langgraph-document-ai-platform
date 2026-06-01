# Framework Extension Guide

Update date: 2026-04-24
Status: Increment 26 complete; next Increment 27

## Purpose

This document describes the standard path for extending the internal framework layer. Its goal is not to replace the architectural blueprint, but to provide a short, practical checklist for adding new workflows, tools, MCP services, adapters and domain packages without breaking current boundaries.

## Basic rules

1. Domain/application code depends on contracts framework, and not on concrete infra adapters.
2. LangGraph remains runtime for orchestration; framework does not introduce a separate DSL.
3. Large payloads are not stored in the workflow state if they can be saved in the store and transferred via ref.
4. External service boundaries use Pydantic schemas from `packages/schemas`.
5. Any extension that affects the API, persistence, MCP or demo flow updates the README, SAO, ADR and release go/no-go demo.

## How to Add Workflow

1. Add a typed state contract to `backend/packages/schemas/workflow` or domain schema module.
2. Implement the workflow class via `framework.workflows.BaseWorkflow` or `SubgraphWorkflow`.
3. For a simple one-step workflow, describe `state_schema()`, `execute()` and, if necessary, `execute_resume()`.
4. For multi-node workflow, override `workflow_nodes(is_resume=...)` and return the list `WorkflowNodeSpec`.
5. Node handler must accept typed state and `WorkflowExecutionContext`; `workflow_name`, `node_name`, `task_id`, `correlation_id`, `is_resume`, `metadata` are available via context.
6. For a reusable subgraph, use `SubgraphWorkflow` and `invoke_as_subgraph(..., parent_context=...)` if you need to pass parent workflow metadata.
7. Pass `task_context.task_id` when using LangGraph checkpointer.
8. Pass `task_context.correlation_id` if the workflow is involved in end-to-end tracing.
9. If the workflow should fall into the audit/read-model, pass `WorkflowNodeEventSink` when creating the workflow.
10. For task lifecycle audit use `TaskApplicationService.build_workflow_node_event_sink()`.
11. If the workflow writes execution details, use single observability keys (`queue_wait_ms`, `duration_ms`, `selected_block_count`, `confidence`, `unresolved_gaps`, `llm_tokens_prompt|completion|total`) instead of ad-hoc naming.
12. Connect workflow via application service or `WorkflowFactory`.
13. If the workflow requires dependencies, register the builder:
   `factory.register_builder("key", lambda retriever: MyWorkflow(retriever=retriever), metadata={...})`.
14. If the workflow does not require dependencies, backward compatible class registration is acceptable:
   `factory.register("key", MyWorkflow)`.
15. For duplicate registration use explicit `replace=True`; missing key and duplicate key should be handled via `WorkflowNotRegisteredError`/`WorkflowRegistrationError`.
16. Add unit tests:
   - invoke path;
- resume path, if workflow is resumable;
- multi-node ordering and context propagation, if `workflow_nodes` is used;
- node event payload, if `WorkflowNodeEventSink` is connected;
- error/interrupt branch, if there is HITL;
- checkpointer thread id behavior, if workflow is long-running.

## How to Add a Tool

1. Add Pydantic input/output schemas.
2. Implement `framework.tools.BaseTool`.
3. Register the tool in `ToolRegistry`.
4. Call the tool via `ToolExecutor` if it is used by the agent/workflow.
5. Pass `ToolContext` with `task_id`, `actor` and, if available, `node_name`, `correlation_id`, `idempotency_key`.
6. Configure `ToolExecutionPolicy` if the tool requires retry/timeout/idempotency behavior.
7. Connect `ToolExecutionAuditSink` if the tool call should fall into audit/read-model.
8. Add contract tests:
   - input validation;
   - output validation;
   - registry lookup;
   - execution context propagation.
- retry/failure path, if retry policy is used;
- idempotency cache path, if the tool can be called again with the same key;
- audit record payload, if audit sink is connected.

## How to Add MCP Service

1. Add MCP schemas to `backend/packages/schemas/mcp`.
2. Implement the service adapter from `framework.mcp.BaseFastMcpService`.
3. The service must accept application/domain service as a dependency.
4. `metadata()` should return `service_name`, `version`, a list of tool names and policy metadata (`operation_scopes`, and for sensitive tools also `auth_policy`/`tool_required_roles`).
5. Add runtime entrypoint to `backend/apps/mcp_*`.
6. Add run/smoke scripts for Linux and Windows, if the service is manual or demo.
7. Add tests to direct service-call without running MCP runtime.
8. If the MCP tool changes the persisted state or performs an approval-sensitive action, use the shared role policy baseline via `_register_toolset(required_roles=...)` and `_authorize_tool(...)`.

## How to Add a Persistence Adapter

1. Start with Protocol/contract in the framework or application layer.
2. Implement concrete adapter in `backend/packages/infra`.
3. If adapter writes to PostgreSQL, add additive SQL migration.
4. If the persistence layer stores the latest snapshot and history at the same time, the latest-by-default contract should remain backward-compatible, and the historical lookup should be added as a separate explicit API/contract.
5. Support fallback only for `dev/stage` if it is compatible with the runtime profile policy.
6. Add tests:
   - in-memory/fallback behavior;
   - SQL payload mapping;
- latest vs explicit historical lookup, if this is a versioned read-model;
- cursor/filter behavior, if it is read-model.

## How to Add Domain Package

1. Create a package under `backend/packages/domain_*`.
2. Keep domain logic independent of FastAPI, Celery and concrete DB clients.
3. Depend on framework contracts and Pydantic schemas.
4. Keep the concrete dependencies assembly in the bootstrap/factory module.
5. Application service should be a thin use-case boundary, and not a place for all domain logic.

## Acceptance Checklist

Before completing the increment:

- unit/integration/e2e tests green;
- release go/no-go demo updated or clearly not affected;
- README reflects new commands/APIs/contracts;
- SAO reflects the current status and GAP;
- ADR added if a new architectural solution is adopted;
- migration/runbook are updated if the database or runtime topology has changed.
