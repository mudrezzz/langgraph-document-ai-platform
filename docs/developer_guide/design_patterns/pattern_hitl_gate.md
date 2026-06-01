# Pattern: HITL Gate Pattern

When to use:

- the solution cannot be fully automated without reviewer sign-off;
- need a repeatable path `needs_changes -> rewrite -> approve`;
- you need to store timeline reviewer actions for auditing.

## Skeleton

`retrieval -> section_authoring -> waiting_human -> needs_changes|approve -> assembly -> completed`

## Runnable example

```bash
.venv/bin/python agent_examples/patterns/hitl_gate/main.py --hitl-decisions needs_changes,approve
```

## Extension points

1. Configure `hitl_max_iterations` and decision list policy.
2. Add reviewer role semantics and policy checks in workflow state.
3. Map in-process transitions to async transport path where needed.

## Anti-patterns

1. Continue pipeline on `reject` as if it was approval.
2. Skip explicit decision history in traceability/audit payload.
3. Mix transport concerns into in-process pattern core logic.
