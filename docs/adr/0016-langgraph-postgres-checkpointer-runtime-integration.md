# ADR-0016: Integration of LangGraph PostgreSQL Checkpointer in Runtime

- Status: Superseded by ADR-0017
- Date: 2026-04-20

## Context

After `Increment 10` task lifecycle, history and status auditing were already persistent, but the `LangGraph` runtime itself did not use the production checkpointer API.

In fact, the checkpoint payload was saved manually through the `TaskApplicationService`, which did not cover the native contract `StateGraph.compile(checkpointer=...)` and the requirements for a stable runtime state.

## Solution

1. Add `PostgresLangGraphCheckpointer` (an implementation of `BaseCheckpointSaver`) to `infra.postgres.checkpoint_store`.
2. Use the `app.checkpoints` table as storage:
- task payload remains in the format `run_id=<task_id>`;
- LangGraph checkpoint namespace is stored in the same storage with the prefix `run_id=lg_thread:*`.
3. Extend `LangGraphPostgresCheckpointStore` with the `build_langgraph_checkpointer()` factory:
- PostgreSQL saver if DSN is available;
- `InMemorySaver` in fallback mode.
4. Connect checkpointer to `BaseWorkflow`:
   - `builder.compile(checkpointer=...)`;
   - `graph.invoke(..., config={"configurable": {"thread_id": ...}})`.
5. Accept `task_context.task_id` as canonical source `thread_id`:
- in `RetrievalApplicationService.start/resume` ensure the presence of `task_id` in `task_context`;
- when checkpointer is enabled, the absence of `task_id` is treated as a runtime configuration error.

## Consequences

Pros:

- LangGraph runtime uses the native checkpoint lifecycle in PostgreSQL;
- `prod` circuit works without fallback and with a single persisted thread state;
- smoke/e2e scripts confirm the correctness of `start/resume` and the checkpoint namespace entry.

Cons:

- at the time of the decision, checkpoint namespace and task payload were separated only by the `run_id` prefix;
- in `Increment 12` storage checkpointer is moved to separate tables (see ADR-0017).
