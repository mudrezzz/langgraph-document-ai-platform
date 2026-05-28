# ADR-0047: Domain authoring traceability and HITL feedback helper extraction

- Status: Accepted
- Date: 2026-04-24

## Context

After ADR-0046, small but still domain stateless helpers remained in `AuthoringApplicationService`:

- conversion of section traceability to `SourceRef` and vice versa;
- update `review_status` by sections;
- human feedback formatting for HITL rewrite.

Although these methods did not control the lifecycle use case, they continued to keep the domain formatting/mapping logic in the application layer.

## Solution

1. Move source-ref/traceability mapping to `OutlinePlanner`.
2. Use `SectionReviewService` as a place to bulk update section review status.
3. Add the `apply_human_feedback(...)` method to the `WriterDraftService` for deterministic formatting reviewer feedback.
4. Save orchestration HITL iteration, task state transitions and artifact persistence in `AuthoringApplicationService`.

## Consequences

Pros:

- application layer is even closer to pure orchestration boundary;
- traceability and rewrite formatting are tested as domain behavior;
- the next slice can be directed to section packets/workflows without returning to the helper logic.

Cons:

- `AuthoringApplicationService` still manages a large use-case lifecycle;
- full-fledged section contracts and template compilation have not yet been allocated.
