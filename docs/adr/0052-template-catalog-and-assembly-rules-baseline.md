# ADR-0052: Template catalog and assembly rules baseline

- Status: Accepted
- Date: 2026-04-24

## Context

After ADR-0051, authoring was already able to compile template specs and assemble template-aware documents, but two important gaps remained:

- there was no separate boundary for `get_template_spec` / template catalog;
- `TemplateSpec` did not store assembly rules as a typed part of the template.

This prevented the move towards reusable template-driven document generation beyond inline payloads.

## Solution

1. Add a minimal `TemplateCatalog` boundary and `InMemoryTemplateCatalog` to `domain_docs`.
2. Expand `TemplateSpec` with the `assembly_rules` field.
3. Teach `TemplateCompiler` to compile and normalize `assembly_rules`, and also set the default rule for section order.
4. Use `assembly_rules` in `DocumentAssembler` to define section order, as well as control the visibility of `Writer Draft` and `Section Traceability`.
5. Save backward compatibility:
- inline `template_payload` is still supported;
- if there is no catalog entry, local compile fallback is used.

## Consequences

Pros:

- a reusable boundary appears for the future `get_template_spec` API/MCP;
- template-driven assembly becomes more explicit and controlled from `TemplateSpec`;
- further transition to the persisted template library is simplified.

Cons:

- catalog is only in-memory baseline for now;
- assembly rules are currently limited to basic deterministic semantics: `section_order`, `include_writer_draft`, `include_traceability`.
