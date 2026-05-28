# ADR 0071: RBAC Boundaries For Sensitive API And MCP Operations

Date: 2026-04-27
Status: Accepted

## Context

By the beginning of Increment 30, the platform already had production-like service boundaries:

- FastAPI endpoints for template governance and authoring HITL;
- FastMCP services for repository, artifact writer, template library, review approval and configuration library;
- unified MCP metadata/policy baseline via `BaseFastMcpService`.

But these boundaries were operationally open: `operation_scope` had already classified the tool as `read|write|action`, but there was no runtime enforcement. This meant that sensitive operations (`publish_template`, `set_template_status`, `submit_hitl_review`, `upsert_config`, `write_artifact`, `upsert_document`) did not have a common minimum authorization boundary.

For the current stage, a full-fledged IAM/SSO layer is not needed, but a production-compatible baseline is needed, which:

- separates read paths from write/approval-sensitive paths;
- works the same for API and MCP;
- does not break current contracts and smoke paths when auth is disabled;
- gives a clear upgrade path to the future auth/audit envelope.

## Solution

Enter the minimum shared RBAC baseline:

1. Added framework-level security helper `framework.security.rbac`.
2. Introduced:
   - `ActorContext`;
   - `RoleBasedAccessPolicy`;
- errors `AuthenticationRequiredError` and `AuthorizationError`;
   - helper `parse_roles(...)`.
3. RBAC enforcement is enabled by the env flag `APP_AUTH_ENABLED=true|false`.
4. When `APP_AUTH_ENABLED=false` policy does not block current flows and maintains backward compatibility.
5. API boundary uses standard headers:
   - `X-Actor-Id`;
   - `X-Actor-Roles`.
6. MCP boundary uses actor context in typed payload fields:
   - `actor`;
   - `roles`.
7. `BaseFastMcpService` expanded auth-aware metadata and enforcement helper:
   - `auth_policy`;
   - `tool_required_roles`;
   - `_authorize_tool(...)`.
8. Enforcement is added only to sensitive operations, read operations remain open.

## Role Matrix

Minimum baseline in this slice:

- `template_admin`:
  - API: `PUT /api/v1/templates/{template_id}`;
  - API: `POST /api/v1/templates/{template_id}/publish`;
  - API: `POST /api/v1/templates/{template_id}/status`;
  - MCP: `upsert_template`, `publish_template`, `set_template_status`.
- `reviewer`:
  - API: `POST /api/v1/tasks/{task_id}/hitl/submit`;
  - MCP: `submit_hitl_review`.
- `config_admin`:
  - MCP: `upsert_config`.
- `artifact_writer`:
  - MCP: `write_artifact`.
- `repository_writer`:
  - MCP: `upsert_document`.
- admin override:
- `admin` or `platform_admin` bypass role-specific checks.

## Consequences

Pros:

- sensitive operations now have a minimal but real protection boundary;
- API and MCP use the same framework-level policy primitive;
- FastMCP metadata now reflects not only scope, but also required roles;
- future auth/audit hardening can be built on top of an already normalized actor context.

Cons:

- this is not a full-fledged identity layer: there are no tokens, SSO, tenant boundaries and signed claims;
- actor context in MCP payload remains trust-based until the appearance of an external auth proxy;
- the write endpoints part of the API is not yet intentionally closed by this slice, if they do not belong to the template governance/HITL boundary.

## Why not a full-fledged IAM now

A full-fledged auth platform would add a lot of infrastructure complexity and would distract from the goal of Increment 30: to bring the reusable service boundary to a production-like baseline. For the current stage it is more important to record:

- where enforcement should live;
- how the actor context is normalized;
- which operations are considered sensitive.

This gives a secure minimal operational envelope without premature enterprise integration.

## What's next

The following security slices can extend baseline to:

- signed auth headers / API gateway integration;
- audit records with actor identity and authorization decision;
- per-endpoint rate limits;
- service-to-service auth for worker/MCP runtime;
- richer role sets and tenant/project-scoped permissions.
