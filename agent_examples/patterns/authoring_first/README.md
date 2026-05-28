# authoring_first - creating an artifact via API

An agent demonstrating the API-driven path: launches a task via an HTTP endpoint,
waits for the result and returns the finished artifact with traceability sections.

---

## What does it do

Sends a request to create a document via `POST /authoring/start`,
synchronously waits for the task to complete and returns an artifact - structured
document with traceability sections (where the data is taken from).

```
Request
  → POST /authoring/start  → task_id
→ GET /task/{task_id} → status (polling until completed)
→ GET /artifact/{id} → artifact + traceability
```

---

## Architectural meaning

This is an **API-driven** pattern: the agent communicates with the deployed backend via HTTP.
Useful when the agent runs in a separate process or on a different machine,
and cannot directly import the framework.

The downside is that you need infrastructure (PostgreSQL), there are network delays,
the route is visible only through the API. For new agents, in-process is recommended
pattern (`retrieval_first`, `device_search`).

---

## File structure

```
authoring_first/
├── agent.py    # AuthoringFirstAgent — start → poll → get artifact
├── config.py   # AuthoringFirstConfig — workflow_mode, draft_strategy, dataset
└── prompts.py # DEFAULT_QUERY - default question
```

---

## Launch

Requires PostgreSQL running with migrations applied:

```bash
bash backend/scripts/postgres_up.sh
bash backend/scripts/postgres_migrate.sh
.venv/bin/python agent_examples/run_example.py --pattern authoring_first
```

---

## What to change first

1. `prompts.py` — change the request (`DEFAULT_QUERY`).
2. `config.py` - ​​switch `workflow_mode` (`standard` / `deep`) or `draft_strategy`.
3. `agent.py` — add post-processing of the artifact to suit your needs.
