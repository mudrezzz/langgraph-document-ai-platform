# Agent Examples

A catalog of runnable Python agent patterns for the framework.
Each pattern is self-contained and optimized for fast onboarding.

## Pattern catalog

| Pattern | What it shows | Execution model | Infrastructure |
|---|---|---|---|
| `retrieval_first` | Document retrieval + EvidencePack | In-process | Not needed |
| `authoring_first` | Deterministic artifact assembly with traceability | In-process | Not needed |
| `hitl_gate` | Reviewer loop (`needs_changes -> approve`) | In-process | Not needed |
| `device_search` | Product search with two HITL checkpoints | In-process | Not needed |

## Architectural context

In-process patterns import framework/domain modules directly and call workflows in memory.
This is the preferred model for new contributor-facing examples.

`hitl_gate` demonstrates the same reviewer-state transitions as async transport flows,
but in an in-process form optimized for fast iteration and tests.

## Patterns

### retrieval_first

Minimal evidence-focused retrieval agent.

Run:

```bash
.venv/bin/python agent_examples/patterns/retrieval_first/main.py
```

### authoring_first

In-process authoring pipeline with explicit steps:
`retrieval -> research -> draft -> review -> section authoring -> assembly`.

Run:

```bash
.venv/bin/python agent_examples/patterns/authoring_first/main.py
```

### hitl_gate

In-process reviewer loop with deterministic HITL decisions.

Run:

```bash
.venv/bin/python agent_examples/patterns/hitl_gate/main.py --hitl-decisions needs_changes,approve
```

### device_search

In-process multi-phase marketplace search with report output.

Run:

```bash
.venv/bin/python agent_examples/run_example.py --pattern device_search
```

## General runner

```bash
.venv/bin/python agent_examples/run_example.py --pattern <name>
```

Available names: `retrieval_first`, `authoring_first`, `hitl_gate`, `device_search`.

Dry-run (no runtime side effects):

```bash
.venv/bin/python agent_examples/run_example.py --pattern retrieval_first --dry-run
```

## Tests

```bash
.venv/bin/pytest -q agent_examples/patterns/retrieval_first/tests/test_agent.py
.venv/bin/pytest -q agent_examples/patterns/authoring_first/tests/test_agent.py
.venv/bin/pytest -q agent_examples/patterns/hitl_gate/tests/test_agent.py
.venv/bin/pytest -q backend/tests/unit/test_agent_examples_contracts.py
.venv/bin/pytest -q agent_examples/tests/test_run_example.py
```

## Structure

```text
agent_examples/
|- run_example.py
|- common/
`- patterns/
   |- retrieval_first/
   |- authoring_first/
   |- hitl_gate/
   `- device_search/
```
