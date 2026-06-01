# ADR-0053: Artifact exporter baseline for template-aware authoring

- Status: Accepted
- Date: 2026-04-24

## Context

After separating out the `DocumentAssembler` and template-aware assembly, the authoring pipeline was already able to build the section-oriented resulting document, but the entire output was still effectively considered markdown-first. Scope `Increment 28` initially included `ArtifactExporter` to separate the deterministic assembly from the artifact output format.

## Solution

1. Add `domain_authoring.ArtifactExporter` as a separate domain service.
2. Leave `DocumentAssembler` responsible only for deterministic assembly content.
3. Delegate `AuthoringApplicationService` to the final export to `ArtifactExporter`.
4. Support baseline export formats:
- `markdown` as the current backward-compatible path;
- `json` as structured template-aware artifact payload.
5. For `json` export use the same `TemplateSpec`, `section_artifacts`, `review_result` and assembly visibility rules (`include_writer_draft`, `include_traceability`).

## Consequences

Pros:

- an explicit boundary appears between assembly and artifact rendering;
- authoring becomes less tied to markdown-only output;
- the path to further export formats (`html`, `docx`, external delivery adapters) becomes easier.

Cons:

- export policy is still minimal and only supports `markdown|json`;
- json export is not yet included in a separate public schema contract, but relies on a deterministic payload shape.
