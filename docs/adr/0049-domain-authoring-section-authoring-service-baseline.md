# ADR-0049: Domain authoring section authoring service baseline

- Status: Accepted
- Date: 2026-04-24

## Context

After ADR-0048, the system already had the typed `SectionContract` and `SectionPacket`, but they remained mainly schemas and metadata boundaries. To continue `Increment 28` we needed a minimal executable domain service that actually consumes the section packet and returns a section-level result without breaking the current single-draft pipeline.

## Solution

1. Add `SectionArtifact` as typed section output.
2. Add `SectionAuthoringService` to `domain_authoring`.
3. On the current slice, build deterministic `section_artifacts` and `SectionDigest` from `SectionPacket`:
- without separate LangGraph workflow;
- without changing public APIs;
- without replacing the current final assembled document.
4. Save `section_artifacts` in `AuthoringTaskState` and artifact metadata.

## Consequences

Pros:

- section packet boundary is now not only typed, but also executable;
- section digests become an observable artifact in the authoring state and metadata;
- the next step to a full-fledged `SectionAuthoringWorkflow` becomes noticeably smaller.

Cons:

- section artifacts do not yet participate in the deterministic final assembly as a primary source;
- service is still deterministic and does not contain a separate reviewer/consistency sub-workflow in sections.
