# ADR-0058: Template management API boundary

- Status: Accepted
- Date: 2026-04-25

## Context

After ADR-0057, the persisted template library already existed as an internal application boundary, and authoring could use versioned templates. But the library itself did not yet have a public service boundary: templates could only be saved through internal container wiring or test setup, which did not correspond to the goal of making reusable templates a manageable part of the platform.

## Solution

1. Add a minimal public API boundary for template management:
   - `PUT /api/v1/templates/{template_id}`;
   - `GET /api/v1/templates/{template_id}`;
   - `GET /api/v1/templates`.
2. Use the existing `TemplateLibraryApplicationService` and `TemplateCompiler` without introducing a parallel template architecture.
3. Keep the scope minimal: only upsert/get/list without delete, review workflow or RBAC.
4. Do not enter Template MCP at this step; first stabilize the HTTP service boundary.

## Consequences

Pros:

- reusable templates can now be controlled and read through the public API;
- the persisted template library becomes the actually used service boundary, and not just the internal wiring layer;
- the next step to template MCP or governance policy is simplified.

Cons:

- The API does not yet have auth/RBAC and approval lifecycle for changing templates;
- no delete/archive semantics and no version promotion policy;
- template management is still limited to the HTTP boundary without a separate MCP/read-model specialization.
