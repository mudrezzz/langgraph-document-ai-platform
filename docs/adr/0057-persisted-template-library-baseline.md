# ADR-0057: Persisted template library baseline

- Status: Accepted
- Date: 2026-04-25

## Context

After ADR-0052 and subsequent authoring slices, the system was already able to collect template-aware documents, but reusable templates still lived either inline in `task_context.template_payload`, or as a local in-memory fallback. This limited the reuse of templates between requests and did not allow persistent reference to a specific version of the template spec in the production-like authoring path.

## Solution

1. Add persisted template library baseline via `TemplateLibraryApplicationService` and `PostgresTemplateStore`.
2. Save the existing `TemplateCatalog` boundary, expanding it with `template_version` support.
3. Translate `AuthoringApplicationService` to resolve path:
- first inline `template_payload`;
- then persisted template library by `template_id/template_version`;
- then existing local compile fallback.
4. Do not introduce a separate public template management API/MCP at this step.
5. Maintain compatibility of the existing authoring API: new fields in `task_context` are optional.

## Consequences

Pros:

- reusable templates can now be stored and reused between authoring requests;
- versioned template resolution becomes part of the production-compatible authoring path;
- the transition to the future template management API/MCP and governance policy is simplified.

Cons:

- the persisted library is currently used only by the internal application layer without a separate public endpoint;
- no policy/approval lifecycle for publishing templates;
- fallback path still allows local compile without store entry, which is useful for bootstrap, but weakens strict governance.
