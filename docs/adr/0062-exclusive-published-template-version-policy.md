# ADR-0062: Exclusive published template version policy

- Status: Accepted
- Date: 2026-04-25

## Context

After ADR-0060, the template library already received a lifecycle `draft|published`, and authoring without an explicit `template_version` began to take the latest published version. But publish semantics were still too weak: one `template_id` could have several published versions at the same time.

For production-like template governance this creates ambiguity:

- default authoring resolution by published template ceases to be an unambiguous policy decision;
- HTTP API, MCP and authoring path formally remain compatible, but operator does not receive the simple invarianta “the template has one active published version”;
- rollback/promotion scenarios become less predictable.

## Solution

1. Leave lifecycle statuses without extension:
   - `draft`;
   - `published`.
2. Change publish semantics so that for one `template_id` there is only one published version at a time.
3. When calling `publish_template(template_id, version)`:
- the selected version receives the status `published`;
- all other published versions of the same `template_id` are automatically demoted to `draft`.
4. Apply this rule equally in the fallback store, PostgreSQL store, HTTP API and MCP path through the existing `TemplateLibraryApplicationService` boundary.
5. Save backward compatibility:
- API/MCP contracts do not change;
- explicit `get_template(template_id, version)` still allows any version to be read regardless of status.

## Consequences

Pros:

- published template resolution becomes unambiguous and easier for operator/runtime;
- publish begins to work as a real promotion step, and not just as adding another active version;
- authoring, HTTP API and MCP use the same exclusive-publish invariant.

Cons:

- publish no longer stores multiple parallel active published branches;
- rollback requires re-publishing the required old version;
- lifecycle governance then closed in ADR-0063: added `deprecated|archived`, explicit status transitions and metadata-based audit.
