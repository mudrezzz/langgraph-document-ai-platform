# ADR-0017: Dedicated Storage for LangGraph Checkpoint Runtime

- Status: Accepted
- Date: 2026-04-20

## Context

In `Increment 11` production checkpointer was connected to runtime, but its data was stored in the common table `app.checkpoints` along with the task payload (`run_id=<task_id>`).

This approach created risks:

- competition for one table between API lifecycle payload and runtime checkpointing;
- complication of operational requests and diagnostics;
- lack of an explicit scheme for the cleanup/retention policy.

## Solution

1. Place LangGraph checkpoint storage in separate tables:
   - `app.langgraph_checkpoints`;
   - `app.langgraph_checkpoint_blobs`;
   - `app.langgraph_checkpoint_writes`.
2. Add migration `0004_langgraph_checkpoint_storage.sql`.
3. Convert `PostgresLangGraphCheckpointer` to work with new tables.
4. Keep the existing `app.checkpoints` for task payload (API lifecycle compatibility does not break).
5. Implement cleanup hooks in checkpointer:
   - `prune(strategy="keep_latest" | "delete")`;
   - `delete_thread`, `copy_thread`.

## Consequences

Pros:

- runtime checkpointing is isolated from task payload storage;
- easier operational audit of checkpointer status;
- there is a basic policy for cleaning up old checkpoint versions.

Cons:

- added additional tables and migration;
- `prune` is currently called only manually (there is no automatic scheduler process).
