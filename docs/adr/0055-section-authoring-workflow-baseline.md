# ADR-0055: Section authoring workflow baseline

- Status: Accepted
- Date: 2026-04-24

## Context

After ADR-0054, authoring already had the typed `SectionContract`, `SectionPacket`, `SectionArtifact`, outline approval point and template-aware deterministic assembly. But section generation was still executed as a direct call to `SectionAuthoringService`, without its own workflow boundary, although `SectionAuthoringWorkflow` was originally included in the scope `Increment 28`.

## Solution

1. Add `domain_authoring.SectionAuthoringWorkflow` as a baseline workflow on top of the existing `SectionAuthoringService` and `SectionReviewService`.
2. Use typed `SectionAuthoringState` and multi-node path:
   - `write_section`;
   - `review_section`;
   - `finalize_section`.
3. For the resume path, support the baseline rewrite hook `rewrite_section`, which applies section-level human feedback without a separate reviewer/HITL subgraph.
4. Convert `AuthoringApplicationService` to build `section_artifacts` via a workflow boundary, without changing external authoring APIs.
5. Do not introduce a separate section persistence/read-model and do not move the workflow section to a separate public endpoint at this step.

## Consequences

Pros:

- section authoring now follows the same framework workflow patterns as retrieval/indexing;
- an obvious growth point appears for section HITL, section review subgraph and selective rewrite;
- application service is less dependent on direct deterministic service call.

Cons:

- workflow is currently launched one section at a time and does not have its own persistence/read-model layer;
- section review still uses the general deterministic reviewer heuristic, without a separate section-specific policy;
- resume path currently only supports a simple feedback append, and not a full-fledged rewrite planner.
