# hitl_gate - in-process reviewer loop

Agent demonstrating a deterministic reviewer-in-the-loop cycle in one Python process.

The pattern simulates `waiting_human -> needs_changes -> waiting_human -> approve -> completed`
without API transport, worker queues, or external infrastructure.

---

## What it does

1. Runs in-process retrieval and builds initial authoring sections.
2. Enters HITL loop and applies reviewer decisions from `--hitl-decisions`.
3. On `needs_changes`, appends reviewer feedback to section drafts.
4. On `approve`, assembles and exports the final artifact.
5. On `reject` or exhausted decisions, returns `task_status=failed`.

```text
query
  -> retrieval
  -> section authoring
  -> waiting_human
  -> decision(needs_changes|approve|reject)
  -> (loop or finalize)
```

---

## Architectural meaning

This is an **in-process** HITL pattern focused on control-flow semantics and auditability.

It is useful when you want to prototype or test reviewer logic quickly,
then map the same state transitions to API/async transport in production.

---

## File structure

```text
hitl_gate/
|- agent.py            # HitlGateAgent response shaping
|- workflow.py         # in-process HITL loop orchestration
|- tools.py            # feedback + steps helpers
|- config.py           # HITL config defaults
|- prompts.py          # DEFAULT_QUERY
|- main.py             # direct entrypoint
|- expected_output/
|  |- result.example.json
|- tests/
|  |- test_agent.py
```

---

## Launch

Direct pattern run:

```bash
.venv/bin/python agent_examples/patterns/hitl_gate/main.py --hitl-decisions needs_changes,approve
```

Through the general runner:

```bash
.venv/bin/python agent_examples/run_example.py --pattern hitl_gate --hitl-decisions needs_changes,approve
```

---

## Decision list

Examples:

- `approve` -> single approval, immediate completion.
- `needs_changes,approve` -> one revision iteration, then completion.
- `reject` -> immediate failure.

---

## What to change first

1. `prompts.py` - update request intent.
2. `config.py` - tune `hitl_max_iterations` and draft/profile settings.
3. `workflow.py` - customize what happens on `needs_changes` and approval criteria.
