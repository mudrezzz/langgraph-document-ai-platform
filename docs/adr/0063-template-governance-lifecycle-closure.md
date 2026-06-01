# ADR-0063: Template governance lifecycle closure

- Status: Accepted
- Date: 2026-04-25

## Context

After ADR-0060 and ADR-0062, the template library already had `draft|published` and exclusive publish invariant. This was enough for baseline authoring, but governance remained unfinished:

- operator could not explicitly mark template version as deprecated or archived;
- HTTP API and MCP did not provide a common explicit lifecycle transition path, except for publish;
- authoring explicit version lookup could still take version without distinction between deprecated and archived;
- governance audit was not recorded in persisted metadata.

For a reusable template library, this is no longer enough: the library has become a public service boundary and must support a minimally production-compatible lifecycle without introducing a separate approval subsystem.

## Solution

1. Close lifecycle statuses reusable template version before typing:
   - `draft`;
   - `published`;
   - `deprecated`;
   - `archived`.
2. Save `publish_template(template_id, version)` as a backward-compatible shortcut, but implement publish via a common status-transition path.
3. Add explicit lifecycle transition boundary:
   - application: `TemplateLibraryApplicationService.set_template_status(...)`;
   - HTTP API: `POST /api/v1/templates/{template_id}/status`;
   - MCP: `set_template_status` tool.
4. Store lightweight governance audit inside the existing `metadata` template record field:
   - `metadata.governance.current_status`;
   - `metadata.governance.updated_at`;
   - `metadata.governance.updated_by`;
   - `metadata.governance.reason`;
   - `metadata.governance.status_history[]`.
5. Fix the minimum transition rules:
   - `draft -> published|deprecated|archived`;
   - `published -> draft|deprecated|archived`;
   - `deprecated -> draft|published|archived`;
- `archived` terminal and is not reactivated.
6. Tighten authoring resolution policy:
- without explicit `template_version` only `published` template is allowed;
- explicit `template_version` can read `draft|published|deprecated`;
- explicit `archived` template for authoring is prohibited.
7. Do not introduce a separate governance store, approval workflow or RBAC subsystem in this slice.

## Consequences

Pros:

- template library receives a complete minimum lifecycle for production-like operations;
- API, MCP, authoring and persistence use a single governance contract;
- archived templates are no longer accidentally used in the authoring path;
- governance audit remains in the existing persistence model without a new architectural branch.

Cons:

- approval chain, reviewer assignment and RBAC are still missing;
- governance audit is stored as metadata JSONB, and not as a separate normalized event store;
- archived version cannot be reactivated without creating a new version or manual DB intervention.
