# ADR-0060: Template library governance status baseline

- Status: Accepted
- Date: 2026-04-25

## Context

After ADR-0057..0059, the template library has already become a persisted service boundary with HTTP API and MCP tools. But all versions of templates remained equal: authoring could take the last saved version by default, even if it was a draft. This is not enough for production authoring.

We need a minimal governance layer that does not turn into a large template management subsystem: a distinction between draft and published versions, plus a clear default template resolution rule.

## Solution

1. Enter the minimum lifecycle status of the reusable template version:
   - `draft`;
   - `published`.
2. Add `status` to the persisted template record, API response and MCP response.
3. Add a separate version publishing operation:
   - HTTP: `POST /api/v1/templates/{template_id}/publish`;
   - MCP tool: `publish_template`.
4. Leave `upsert` compatible:
- by default version is created as `draft`;
- with an explicit `status=published` upsert ends with the publish step.
5. Change default authoring-resolution:
- if `task_context.template_version` is not passed, authoring takes only `published` template;
- if version is passed explicitly, it is allowed to read a specific version regardless of the status;
- inline `template_payload` still has the highest priority.

## Consequences

Pros:

- authoring by default stops accidentally using unpublished drafts;
- templates receive a minimal production-compatible governance layer without heavy approval workflow;
- HTTP API, MCP and authoring path use the same status-aware persistence boundary.

Cons:

- baseline lifecycle then expanded to `draft|published|deprecated|archived` and explicit status transitions in ADR-0063;
- detail publish policy for active published-version clarified in ADR-0062;
- approval workflow and RBAC still remain outside the current scope.
