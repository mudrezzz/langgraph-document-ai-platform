# ADR-0068: Review/Approval MCP Boundary

- Status: Accepted
- Date: 2026-04-26

## Context

By the beginning of Increment 30, the platform already has:

- authoring/HITL API (`GET /api/v1/tasks/{task_id}/hitl`, `POST /api/v1/tasks/{task_id}/hitl/submit`);
- persistence/read-model action reviewer layer (`app.hitl_actions`);
- reviewer aggregates endpoint `GET /api/v1/hitl/observability/summary`;
- MCP boundaries for retrieval, repository, artifact writer and template library.

But the reviewer/manual approval path was still only available through the HTTP API. For a production-like MCP surface, a minimum boundary is needed through which an external agent or operator can:

- view the current HITL status of the task;
- read the history of reviewer actions;
- send the reviewer the decision;
- get an aggregated summary of reviewer load and decisions.

In this case, you cannot duplicate the existing authoring/HITL architecture or introduce a separate reviewer-specific runtime stack.

## Solution

1. Add a separate FastMCP service `review-approval-mcp`.
2. Add typed MCP contracts to `schemas.mcp.review_approval`.
3. Give the service a minimum set of tools:
   - `get_hitl_status`;
   - `list_hitl_actions`;
   - `submit_hitl_review`;
   - `get_hitl_observability_summary`.
4. Implement a boundary on top of the existing application/read-model layer:
   - `AuthoringApplicationService.hitl_status(...)`;
   - `AuthoringApplicationService.list_hitl_actions(...)`;
   - `AuthoringApplicationService.submit_hitl(...)`;
   - `AuthoringApplicationService.hitl_observability_summary(...)`.
5. For submit path, reuse the existing `AuthoringAsyncDispatcher` so that MCP and HTTP path put continuation in the same async plane.
6. Map internal application layer errors to MCP-friendly `ValueError`, without disclosing the internal state payload shape as a public contract.

## Consequences

Pros:

- MCP surface now covers not only retrieval/repository/artifact/template operations, but also reviewer/HITL decision path;
- reviewer tools use the same production-compatible orchestration and the same persistence/read-model layer as the HTTP boundary;
- a new parallel review-specific architecture does not appear.

Cons:

- boundary does not yet add unified auth/RBAC/rate-limit policy for MCP services;
- observability MCP tool reuses current read-model aggregates and does not yet resolve SLA buckets/day-week dashboards;
- manual approval path still depends on existing authoring task semantics (`waiting_human`, iteration limits, idempotency rules).
