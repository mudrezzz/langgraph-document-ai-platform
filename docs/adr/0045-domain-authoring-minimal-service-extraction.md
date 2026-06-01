# ADR-0045: Minimal domain_authoring service extraction

- Status: Accepted
- Date: 2026-04-24

## Context

After `Increment 27` was closed, the authoring path already supported sync/async execution, HITL, artifact traceability and LLM fallback, but most of the authoring domain logic remained inside `AuthoringApplicationService`.

`Increment 28` requires a gradual transition to a separate `domain_authoring` package without breaking existing APIs and without a lot of refactoring in one slice.

## Solution

1. Add package `backend/packages/domain_authoring`.
2. On the first slice, add the minimum domain services:
   - `OutlinePlanner`;
   - `SectionReviewService`;
   - `DocumentAssembler`.
3. Save `AuthoringApplicationService` as application/orchestration boundary:
   - retrieval task lifecycle;
   - async dispatch;
   - HITL state transitions;
   - artifact persistence;
   - task/artifact link.
4. Integrate new domain services via dependency injection with default implementations.
5. Do not change external APIs/contracts on this slice.

## Consequences

Pros:

- real decomposition of the authoring domain begins without regression of public contracts;
- reviewer/outline/assembly logic becomes isolated and directly testable;
- the following slices can separately include outline planning, section workflows and assembly contracts.

Cons:

- `AuthoringApplicationService` remains a major orchestrator for now;
- writer/research/traceability/HITL logic is not yet fully included in `domain_authoring`.
