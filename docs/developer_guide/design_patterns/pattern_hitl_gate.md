# Pattern: HITL Gate Pattern

When to use:

- the solution cannot be fully automated without reviewer sign-off;
- need a repeatable path `needs_changes -> rewrite -> approve`;
- you need to store timeline reviewer actions for auditing.

## Skeleton

`authoring/start_async -> waiting_human -> hitl/submit -> resume -> completed`

## Runnable example

```bash
bash backend/scripts/async_up.sh
.venv/bin/python agent_examples/run_example.py --pattern hitl_gate --hitl-decisions needs_changes,approve
```

## Extension points

1. Set up max iterations and timeout via `APP_HITL_*`.
2. Add reviewer roles/RBAC policy for sensitive decisions.
3. Add your observability checks to the release gate.

## Anti-patterns

1. Don't check `expected_iteration`/idempotency when submitting.
2. Continue the pipeline at `reject` as at `approve`.
3. Do not close async resources after smoke/rehearsal.
