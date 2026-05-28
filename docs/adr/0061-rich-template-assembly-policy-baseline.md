# ADR-0061: Rich template assembly policy baseline

- Status: Accepted
- Date: 2026-04-25

## Context

After ADR-0052, ADR-0053 and ADR-0060, the reusable template library was already able to store `TemplateSpec`, and authoring already supported template-aware section contracts, deterministic assembly and `markdown|json` export. But the assembly policy remained too narrow:

- `assembly_rules` actually controlled only `section_order`, `include_writer_draft`, `include_traceability`;
- optional/conditional sections could not be described in the template payload itself;
- JSON export and section traceability for custom templates lagged behind richer assembly semantics;
- traceability by default remained mostly release-readiness specific.

For a reusable authoring framework, this is not enough: templates are needed not only for one demo report, but also for a wider class of documents, where appendix sections, evidence-driven sections and reviewer-only sections should be included deterministically from policy, and not from ad hoc orchestration logic.

## Solution

1. Expand normalized `TemplateSpec.sections` with a minimal richer policy set:
   - `required`;
   - `include_if_has_evidence`;
   - `include_if_review_status`;
   - `section_group`.
2. Expand normalized `TemplateSpec.assembly_rules` with fields:
   - `include_sections`;
   - `exclude_sections`;
   - `allowed_section_groups`.
3. Leave `DocumentAssembler` as a single source of truth for section selection:
- required sections are always included if they are not included in the explicit exclude/group filter;
- optional sections are included according to evidence or review status policy;
- include/exclude/group filters are used as a deterministic assembly gate.
4. Make `ArtifactExporter` reuse the same section-selection path so that markdown and JSON do not differ in the composition of sections.
5. Make `OutlinePlanner` template-aware:
- if there is a `TemplateSpec` and `SectionContract` list, traceability is built according to the same template sections, and not according to the hardcoded release-readiness layout.
6. Save backward compatibility:
- the old release-readiness fallback path remains working;
- existing authoring API does not change;
- templates without new fields continue to behave as before.

## Consequences

Pros:

- reusable templates can now describe optional appendix/evidence/reviewer sections without changing the application orchestration;
- markdown export, JSON export and traceability become consistent for custom templates;
- richer template semantics remain in the existing `TemplateCompiler` / `DocumentAssembler` / `OutlinePlanner`, without parallel architecture.

Cons:

- policy is intentionally minimal so far: there are no arbitrary boolean expressions, nested rule engines or per-section rendering strategies;
- traceability still derives source refs from existing contracts/evidence heuristics, and not from a separate section planning graph;
- richer authoring layout policy is closed in this ADR, and template governance lifecycle is then closed in ADR-0063.
