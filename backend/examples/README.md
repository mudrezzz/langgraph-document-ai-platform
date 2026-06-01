# Framework Examples Catalog

Update date: 2026-04-30
Status: Active quickstart gallery

This directory shows minimal runnable cases so that a developer can see in 5-15 minutes:

- how to quickly raise a useful agent flow;
- what the working path and expected result look like;
- how to move from an example to an extension for your own use case.

## Quick start (Linux)

1. Get PostgreSQL up and apply migrations:

```bash
bash backend/scripts/postgres_up.sh
bash backend/scripts/postgres_migrate.sh
```

2. View the list of examples:

```bash
.venv/bin/python backend/examples/quickstart_agents.py --list
```

3. Run any example:

```bash
.venv/bin/python backend/examples/quickstart_agents.py --example retrieval_faq_assistant --execute
```

## Examples

1. `retrieval_faq_assistant`  
   Pattern: `Retrieval-First Agent`  
What it shows: fast retrieval path with evidence pack.

2. `authoring_policy_brief`  
   Pattern: `Authoring-First Agent`  
What it shows: authoring flow with multi-step mode and traceability.

3. `hitl_review_loop`  
   Pattern: `HITL Gate Pattern`  
What it shows: async authoring + iterative review (`needs_changes -> approve`).
Before starting, you need to raise the async plane:

```bash
bash backend/scripts/async_up.sh
```

## Dry-run mode (without startup)

To test the resulting command without executing:

```bash
.venv/bin/python backend/examples/quickstart_agents.py --example authoring_policy_brief
```

`dry-run` is useful when needed:

- view launch parameters;
- add your args via `--extra-arg`;
- embed launch into CI/local script.

Example:

```bash
.venv/bin/python backend/examples/quickstart_agents.py \
  --example retrieval_faq_assistant \
  --extra-arg --port \
  --extra-arg 8210
```

## How to test examples (for you)

1. Quick unit tests of the example catalog:

```bash
.venv/bin/pytest -q backend/tests/unit/test_example_quickstart_agents.py
```

2. Contract docs tests (check links to examples/patterns):

```bash
.venv/bin/pytest -q backend/tests/unit/test_developer_guide_contracts.py
```

3. Real smoke path of one example:

```bash
.venv/bin/python backend/examples/quickstart_agents.py --example retrieval_faq_assistant --execute
```

## Cleanup

After persecution:

```bash
bash backend/scripts/async_down.sh
bash backend/scripts/postgres_down.sh --remove-volumes
```
