# hitl_gate - asynchronous review loop with HITL

Agent demonstrating reviewer-in-the-loop via async API: starts a task,
pollit status, at `waiting_human` submits the reviewer's decision and repeats the cycle.

---

## What does it do

Starts artifact creation via `start_async`, waits until the task asks
human review (`waiting_human`), submits a solution (`needs_changes` or
`approve`) and repeats until the final `completed`.

```
POST /authoring/start_async → task_id
  → poll: waiting_human?
→ GET /hitl/{task_id}/status - current iteration
→ POST /hitl/{task_id}/submit - solution: needs_changes / approve
→ poll again...
  → completed → GET /artifact/{id}
```

Each HITL solution is idempotent: the agent transmits `idempotency_key`,
so that resending does not create duplicates.

---

## Architectural meaning

Shows the mechanics of HITL at the API protocol level - how a task moves between
states `running → waiting_human → running → completed`, as an agent
programmatically plays the role of a reviewer.

In a real scenario, the decision (`needs_changes` / `approve`) is made by a person
via UI; in the example it is passed via `--hitl-decisions` for automation.

---

## File structure

```
hitl_gate/
├── agent.py # HitlGateAgent - async loop with polling + HITL submissions
├── config.py   # HitlGateConfig — hitl_required, workflow params
└── prompts.py # DEFAULT_QUERY - default query
```

---

## Launch

Requires PostgreSQL, migrations and async worker:

```bash
bash backend/scripts/postgres_up.sh
bash backend/scripts/postgres_migrate.sh
bash backend/scripts/async_up.sh

.venv/bin/python agent_examples/run_example.py \
  --pattern hitl_gate \
  --hitl-decisions needs_changes,approve
```

Stop the infrastructure after starting:

```bash
bash backend/scripts/async_down.sh
bash backend/scripts/postgres_down.sh --remove-volumes
```

---

## Parameter `--hitl-decisions`

List of solutions for sequential application separated by commas.
The agent spends one for each `waiting_human`.

Examples:
- `approve` - ​​one approval, if the task waits once
- `needs_changes,approve` - ​​first reject, then approve
- `needs_changes,needs_changes,approve` - ​​two rejections, then approval

---

## What to change first

1. `prompts.py` — change the request.
2. `config.py` — change `hitl_required` or `workflow_mode`.
3. `agent.py::run()` — replace `decisions` from the parameter with a real UI input.
