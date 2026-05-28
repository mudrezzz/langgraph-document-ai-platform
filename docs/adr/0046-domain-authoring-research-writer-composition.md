# ADR-0046: Domain authoring research and writer composition extraction

- Status: Accepted
- Date: 2026-04-24

## Context

After ADR-0045 reviewer/outline/assembly logic was already moved to `domain_authoring`, but `AuthoringApplicationService` still contained:

- building a research summary from evidence;
- deterministic writer draft composition;
- LLM prompt composition.

This left the application layer overloaded with domain-specific text formatting and made it difficult to further highlight section-oriented authoring workflows.

## Solution

1. Add two more stateless services to `domain_authoring`:
   - `ResearchSummaryBuilder`;
   - `WriterDraftService`.
2. Leave only the orchestration writer stage in `AuthoringApplicationService`:
- select `draft_strategy`;
- call external `IChatModelGateway`;
- fallback policy and metadata of the result.
3. Transfer new domain services to the application layer via dependency injection with default implementations.
4. Do not change external authoring/HITL API and artifact contracts.

## Consequences

Pros:

- research/writer text composition is now tested separately from orchestration and LLM gateway;
- the boundary between domain formatting and application orchestration has become clearer;
- the next slice can carry section packets/workflows without mixing with prompt/draft formatting.

Cons:

- the solution still does not highlight a full section authoring workflow;
- application layer still retains lifecycle orchestration and HITL rewrite policy.
