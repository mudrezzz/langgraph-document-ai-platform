# ADR-0048: Domain authoring section contracts and packets baseline

- Status: Accepted
- Date: 2026-04-24

## Context

After ADR-0047, the domain layer already covered the outline/review/assembly/research/writer composition, but the authoring pipeline still operated only with the general draft and traceability sections. In `Increment 28`, the next logical step is to introduce typed section-oriented contracts, without switching the entire pipeline to section-by-section execution at once.

## Solution

1. Add new typed schemas:
   - `SectionContract`;
   - `SectionPacket`.
2. Add `SectionContractBuilder` to `domain_authoring`.
3. On the current slice, build release-readiness section contracts from evidence/review context and save them in:
   - `AuthoringTaskState.section_contracts`;
   - artifact metadata.
4. Do not change public APIs and do not introduce a separate workflow section for now.

## Consequences

Pros:

- a typed boundary appears for the next step to section-by-section authoring;
- section intent and preferred source refs become observable in state and artifact metadata;
- the transition to outline approval/section workflows can be done gradually, without demolishing the current pipeline.

Cons:

- the pipeline still writes a single draft, and not separate section drafts;
- `SectionPacket` is currently fixed as a baseline contract and is not yet used by a separate workflow runner.
