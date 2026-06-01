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
| `async_batch` | Batched query processing for long-running style workloads | In-process | Not needed |
| `mcp_tool_facade` | Core-agent logic exposed through MCP-style tool adapter | In-process | Not needed |

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

### async_batch

In-process batched retrieval with chunking and partial-failure contract.

Run:

```bash
.venv/bin/python agent_examples/patterns/async_batch/main.py
```

### mcp_tool_facade

In-process pattern that separates core agent logic from MCP-style tool adapter.

Run:

```bash
.venv/bin/python agent_examples/patterns/mcp_tool_facade/main.py
```

## General runner

```bash
.venv/bin/python agent_examples/run_example.py --pattern <name>
```

Available names: `retrieval_first`, `authoring_first`, `hitl_gate`, `device_search`, `async_batch`, `mcp_tool_facade`.

Dry-run (no runtime side effects):

```bash
.venv/bin/python agent_examples/run_example.py --pattern retrieval_first --dry-run
```

## Tests

Unified harness:

```bash
python agent_examples/tests/run_harness.py --lane fast
python agent_examples/tests/run_harness.py --lane full
```

Optional required external smoke (`device_search`):

```bash
RUN_EXTERNAL_LLM_TESTS=1 OPENROUTER_API_KEY=... python agent_examples/tests/run_harness.py --lane full --require-external-llm-smoke
```

Equivalent direct checks:

```bash
.venv/bin/pytest -q agent_examples/patterns/retrieval_first/tests/test_agent.py
.venv/bin/pytest -q agent_examples/patterns/authoring_first/tests/test_agent.py
.venv/bin/pytest -q agent_examples/patterns/hitl_gate/tests/test_agent.py
.venv/bin/pytest -q agent_examples/patterns/async_batch/tests/test_agent.py
.venv/bin/pytest -q agent_examples/patterns/mcp_tool_facade/tests/test_agent.py
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
   |- device_search/
   |- async_batch/
   `- mcp_tool_facade/
```
