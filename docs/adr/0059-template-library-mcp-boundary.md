# ADR-0059: Template Library MCP boundary

- Status: Accepted
- Date: 2026-04-25

## Context

After ADR-0057 and ADR-0058, the persisted template library already existed as an application boundary and as a public HTTP API. But in the MCP circuit, reusable templates were not yet available: agents and automation paths had to either work via HTTP or bypass the service boundary with direct container wiring.

This is inconvenient for platform-wide authoring: templates must be available in the same way that repository documents, retrieval search and generated artifacts are already available. In this case, you cannot introduce a separate MCP-specific template architecture, otherwise template compilation and persistence will begin to diverge between HTTP, authoring and MCP paths.

## Solution

1. Add a separate FastMCP boundary `template-library-mcp`.
2. Enable only minimal tools:
   - `upsert_template`;
   - `get_template`;
   - `list_templates`.
3. Implement MCP service on top of the existing `TemplateLibraryApplicationService`:
- `upsert_template` first calls `compile_template(...)`, then saves the compiled `TemplateSpec`;
- `get_template` and `list_templates` read the same persisted records as HTTP/API and authoring path.
4. Add typed MCP schemas to `schemas.mcp.template_library`.
5. Add runtime/smoke scripts using the same operational pattern that is already used for Retrieval/Repository/Artifact Writer MCP.

## Consequences

Pros:

- reusable templates are now available via MCP, which makes the template library part of the general agent-facing service surface;
- MCP path reuses existing compiler/persistence boundaries and does not diverge from the HTTP/API path;
- authoring automation can be built via MCP tools without additional glue logic.

Cons:

- MCP boundary is currently limited only to CRUD-like read/write path without delete/archive/version-promotion semantics;
- no auth/RBAC and governance policy for template changes;
- template governance lifecycle closure made in ADR-0063.
