# ADR-0051: Template-aware deterministic assembly

- Status: Accepted
- Date: 2026-04-24

## Context

After ADR-0050, authoring already supported `TemplateCompiler`, template-aware section contracts and `section_artifacts`, but the final deterministic assembly still remained essentially release-readiness specific and relied mainly on the general writer draft. This limited reuse for other document-generation scenarios.

## Solution

1. Extend `DocumentAssembler` so that it can assemble a document from:
   - `TemplateSpec`;
   - `section_artifacts`;
- reviewer summary and traceability.
2. Save backward compatibility:
- without template/section artifacts assembler continues the old release-readiness path;
- if template-aware data is available, section-oriented deterministic assembly is used.
3. Do not change public APIs and artifact contract shapes.

## Consequences

Pros:

- deterministic assembly becomes reusable for various template-driven tasks;
- section artifacts begin to influence the final document, and not just live in the metadata;
- the next step towards a full section-by-section authoring pipeline is simplified.

Cons:

- assembly does not yet use separate assembly rules/catalog beyond inline `TemplateSpec`;
- the writer draft is still retained as part of the final document for observability and backwards compatibility.
