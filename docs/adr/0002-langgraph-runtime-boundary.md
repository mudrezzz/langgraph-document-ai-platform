# ADR-0002: LangGraph as the only orchestration runtime

- Status: Accepted
- Date: 2026-04-17

## Context

It is necessary to eliminate the blurring of orchestration logic between the UI, prompt code and integration scripts.

## Solution

- All complex processes are implemented as workflow/subgraph based on LangGraph.
- The Framework layer provides thin wrappers (`BaseWorkflow`, `SubgraphWorkflow`), but does not replace LangGraph.
- Creation of an internal DSL for orchestration is prohibited.

## Consequences

Pros:

- transparent lifecycle of tasks;
- unified interrupt/resume/checkpoint model;
- clear tracing of graph transitions.

Cons:

- additional requirements for the engineering discipline when designing state.
