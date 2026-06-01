# retrieval_first - in-process document search

A minimal agent showing how to build the agent as a Python composition
on top of framework contracts - without HTTP, without infrastructure, just `invoke()`.

---

## What does it do

Takes a text question, runs it through `RetrievalWorkflow` directly
in memory, returns `EvidencePack`: a set of relevant document blocks
with sources, confidence notes and a list of unresolved spaces.

```
Request
  → RetrievalWorkflow.invoke()
      → EvidencePack
selected_blocks — document blocks
selected_sources — sources (doc_id, version, block_id)
confidence_notes - explanations of confidence
unresolved_gaps - what was not found
```

---

## Architectural meaning

This is an **in-process** pattern: the agent imports the framework as a library
and calls `workflow.invoke()` directly. No network delays
there is no need to raise the backend, the entire route is visible in Python objects.

This is a target model for new agents. `authoring_first`, `hitl_gate`,
`device_search`, `async_batch`, and `mcp_tool_facade` use the same in-process model.

---

## File structure

```
retrieval_first/
├── agent.py # RetrievalFirstAgent - calls workflow and generates a response
├── workflow.py # run_retrieval_workflow() - a thin wrapper over RetrievalWorkflow
├── tools.py # build_default_filters() - document filters for search
├── config.py   # RetrievalFirstConfig — case_dataset_id, requester
├── prompts.py # DEFAULT_QUERY - default question
├── main.py # entry point
└── tests/ # unit + smoke tests
```

---

## Launch

```bash
.venv/bin/python agent_examples/patterns/retrieval_first/main.py
```

Through the general runner:

```bash
.venv/bin/python agent_examples/run_example.py --pattern retrieval_first
```

Dry-run (test without real calls):

```bash
.venv/bin/python agent_examples/run_example.py --pattern retrieval_first --dry-run
```

---

## Tests

```bash
.venv/bin/pytest -q agent_examples/patterns/retrieval_first/tests/test_agent.py
```

---

## What to change first

1. `prompts.py` — change the question (`DEFAULT_QUERY`).
2. `tools.py` — change `document_types` and search filters.
3. `config.py` — switch `case_dataset_id` or `requester`.
