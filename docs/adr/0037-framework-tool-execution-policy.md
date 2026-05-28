# ADR-0037: Framework tool execution policy

- Status: Accepted
- Date: 2026-04-24

## Context

After `Increment 25` the framework layer had basic contracts for agents/tools/workflows, but `ToolExecutor` remained a minimal lookup-wrapper on top of `ToolRegistry`. The target architecture requires that tools can be safely used inside agents/workflows/MCP with a single lifecycle:

- retry;
- timeout accounting;
- idempotency;
- audit;
- propagation task/node/correlation metadata.

If you leave these concerns in application/domain services, different workflows will begin to implement retry/idempotency/audit differently.

## Solution

1. Expand `ToolContext` with fields:
   - `node_name`;
   - `correlation_id`;
   - `idempotency_key`.
2. Add `ToolExecutionPolicy`:
   - `max_attempts`;
   - `timeout_sec`;
   - `idempotency_enabled`;
   - `audit_enabled`.
3. Add audit contract:
   - `ToolExecutionRecord`;
   - `ToolExecutionAuditSink`;
- `InMemoryToolExecutionAuditSink` for unit/dev scripts.
4. Maintain backward compatibility:
- `ToolExecutor(registry).execute(tool_name, command, context)` remains the main call;
- without explicit policy, the behavior remains one-time execution without the mandatory audit sink.
5. Fix contract tests for retry/idempotency/audit behavior.

## Consequences

Pros:

- framework tools received a single runtime behavior without changing application services;
- future agents/workflows/MCP services will be able to use one policy surface;
- idempotency and audit metadata are now standardized at the framework context level.

Cons:

- timeout is still an accounting/detection after a sync tool call, and not a preemptive cancellation;
- idempotency cache is local to the `ToolExecutor` instance; production persistence policy will be added as a separate slice for a unified execution plane.
