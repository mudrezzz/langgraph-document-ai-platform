# ADR-0070: Unified FastMCP Service Policies

- Status: Accepted
- Date: 2026-04-27

## Context

By the middle of Increment 30, the platform already has several FastMCP boundaries:

- retrieval;
- repository;
- artifact writer;
- template library;
- review/approval;
- configuration library.

All of them were built according to one general pattern, but in fact metadata and error mapping remained partially ad-hoc: each service itself collected `tool_names`, there was no common `service_scope` field, a single `operation_scope` was not fixed, and error mapping in MCP-friendly `ValueError` was repeated manually in each service.

For a production-like MCP surface, this level of discrepancy is no longer desirable: new boundaries will copy different local patterns, and the external integrator will not be able to count on a uniform service contract.

## Solution

1. Extend `BaseFastMcpService` as a single policy carrier for FastMCP boundaries.
2. Fix a single metadata contract for all MCP services:
   - `service_name`;
   - `version`;
   - `transport=fastmcp`;
   - `service_scope`;
   - `policy_version=mcp-policy-v1`;
   - `tool_names`;
   - `operation_scopes`;
   - `input_validation` / `output_validation`;
   - `error_mapping`;
   - `audit_payload_fields`.
3. Add helper `_register_toolset(...)`, which:
- validates tool naming (`snake_case`);
- registers a single `tool_names` list;
- calculates or accepts explicit `operation_scope` for each tool.
4. Use a simple operation-scope model:
- `read` for `get/list/lookup/search/find/compare`;
- `write` for `upsert/write/publish/set/submit`;
- `action` for execution-style tools like `build_evidence_pack`.
5. Add helper `_operation_error(...)` and switch MCP services to a single error mapping instead of manual `raise ValueError(str(exc))` in each implementation.
6. Do not break existing tool names and runtime entrypoints; policy change should be additive and backward-compatible for current callers.

## Consequences

Pros:

- all FastMCP boundaries now provide a uniform metadata payload;
- it’s easier to add new MCP services using one template;
- auth/RBAC, audit and operational runbook are easier to build on top of an already unified metadata surface;
- tests can check the MCP policy contract centrally, and not just per-service behavior.

Cons:

- metadata payload has become wider than in earlier MVP slices;
- `operation_scope` is still heuristic-based and may require refinement when more complex tool semantics appear;
- unified error mapping is still based on `ValueError`, and not on a separate richer MCP error taxonomy.
