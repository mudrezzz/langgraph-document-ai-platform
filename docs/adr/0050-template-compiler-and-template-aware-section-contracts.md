# ADR-0050: TemplateCompiler and template-aware section contracts

- Status: Accepted
- Date: 2026-04-24

## Context

After ADR-0049, the authoring domain already supported section contracts, packets, and deterministic section authoring, but sections were still effectively locked into the release-readiness use case. For a broader set of analytical scenarios, a template-aware layer was needed that could define the section structure without rewriting the authoring orchestration.

## Solution

1. Add `TemplateCompiler` to `domain_docs`.
2. Leave `TemplateSpec` as a typed template contract and allow compilation from `task_context.template_id` + `task_context.template_payload`.
3. Extend `SectionContractBuilder` so that it can build section contracts from `TemplateSpec`.
4. Integrate template-aware path into `AuthoringApplicationService` as an optional internal behavior:
   - default template: `release_readiness`;
- custom templates via `task_context.template_id` and `task_context.template_payload`.
5. Do not change the public API.

## Consequences

Pros:

- the authoring layer is no longer reserved only for the release-readiness report;
- a reusable template boundary appears for future document-generation scenarios;
- section contracts and section artifacts can now be built from an externally specified template spec.

Cons:

- template storage/catalog is not yet available, inline payload is used in `task_context`;
- deterministic assembly is not yet completely template-driven.
