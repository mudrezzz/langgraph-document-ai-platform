# ADR-0007: LangGraph runtime execution in BaseWorkflow

- Status: Accepted
- Date: 2026-04-17

## Context

The basic workflow was previously a placeholder implementation without an actual graph runtime. To comply with the architectural principle "LangGraph as a single orchestration runtime" you need to translate invoke/resume into the graph runtime model.

## Solution

1. Extend `BaseWorkflow`:
- `compile()` builds LangGraph for invoke/resume paths;
- `invoke()` and `resume()` execute the compiled graph;
- in fallback mode (if runtime is not available) compatibility is maintained.
2. Enter explicit extension points:
- `execute(state)` — invoke business logic;
- `execute_resume(state)` - resume business logic.
3. Translate `RetrievalPackWorkflow` to `execute/execute_resume` instead of overriding invoke/resume.

## Consequences

Pros:

- lifecycle workflow began to comply with the LangGraph-first approach;
- a unified execution model for new workflows;
- it’s easier to expand interrupt/resume and graph branches.

Cons:

- additional checkpointer/persistence integration for production is required;
- the complexity of the base workflow layer has increased compared to placeholder.
