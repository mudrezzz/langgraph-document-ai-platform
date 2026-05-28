# Agent Examples Demo Program (In-Process)

Update date: 2026-04-30
Status: In Progress (DOC-030 completed; DOC-031..DOC-035 pending)

## 1. Product Goal

Make `agent_examples/` a separate product input for external developer.

Key UX:

1. Open one folder.
2. Read the Python code of the agent without diving into the internals of the framework.
3. Run `main.py` with one command.
4. Change a few files (`prompts/config/tools`) and quickly get your agent.

## 2. Problem Statement

The current examples mainly show the API-driven integration path (`framework as service`).

For the scenario “I’m creating a new agent using the framework”, a different format is needed:

- in-process composition over framework contracts;
- demonstration of `agent/workflow/tools` code as a library;
- minimal dependence on the API-boundary/transport layer.

## 3. Non-Negotiable Principles

1. Primary path = in-process framework usage, not HTTP client.
2. One pattern = one self-contained subfolder with the same structure.
3. `python .../main.py` should be the main launch method.
4. Fast deterministic mode is required for onboarding.
5. Production-like mode should be optional, but documented.
6. Each example has local tests and an expected output proof.

## 4. Target Information Architecture

```text
agent_examples/
  README.md
  getting_started.md
  design_patterns/
    README.md
    retrieval_first.md
    authoring_first.md
    hitl_gate.md
    async_batch.md
    mcp_tool_facade.md
  patterns/
    retrieval_first/
      README.md
      main.py
      agent.py
      workflow.py
      tools.py
      prompts.py
      config.py
      sample_input/
      expected_output/
      tests/
    authoring_first/
      README.md
      main.py
      agent.py
      workflow.py
      tools.py
      prompts.py
      config.py
      sample_input/
      expected_output/
      tests/
    hitl_gate/
      README.md
      main.py
      agent.py
      workflow.py
      tools.py
      prompts.py
      config.py
      sample_input/
      expected_output/
      tests/
  shared/
    runtime_profiles.py
    fixtures.py
    assertions.py
    output_render.py
  tests/
    test_examples_contracts.py
```

## 5. Pattern Library Scope

## 5.1 P0 Patterns

1. Retrieval-First Agent
2. Authoring-First Agent
3. HITL Gate Pattern

## 5.2 P1 Patterns

1. Async Batch Pattern
2. MCP Tool Facade Pattern

## 6. Pattern Blueprint Contract

Each pattern must contain:

1. `agent.py`: composition root and public run path.
2. `workflow.py`: orchestration steps/state transitions.
3. `tools.py`: local tools and typed I/O contracts.
4. `prompts.py`: prompt templates and minimal explanation.
5. `config.py`: deterministic/prod-like profiles.
6. `main.py`: CLI launch and print the result.
7. `README.md`: use case, run steps, expected output, extension points.
8. `tests/`: unit + smoke for the current pattern.
9. `expected_output/`: reference result for quick manual checking.

## 7. Execution Modes

1. Quick deterministic mode:
- launch without external services by default;
- predictable output for onboarding and CI.
2. Production-like mode:
- includes infrastructure dependencies;
- used for parity-check and extended checking.

## 8. Test Strategy

1. Pattern Unit Tests:
- checking the workflow/tools/prompt shaping logic.
2. Pattern Smoke Tests:
- start `main.py` end-to-end and check expected output.
3. Determinism Tests:
- same input => same output in quick mode.
4. Structure Contracts:
- all pattern folders contain required files.
5. Docs Contracts:
- the commands in `README` are valid and reproducible.
6. CI lanes:
   - fast lane: unit + contracts;
- full lane: smoke all pattern demos.

## 9. Implementation Roadmap

## 9.1 P0 (must-have)

1. Replatform `retrieval_first` in in-process style.
2. Replatform `authoring_first` in in-process style.
3. Replatform `hitl_gate` in in-process style.
4. Unify shared helpers for pattern folders.
5. Connect examples contract tests and dry/smoke checks in the CI path.
6. Update root README + developer guide as primary entrypoint to `agent_examples/`.

## 9.2 P1 (next)

1. Add `async_batch` pattern demo.
2. Add `mcp_tool_facade` pattern demo.
3. Add template `create-your-agent` (copy-and-modify starter kit).

## 10. Definition of Done (per pattern)

1. One command-run from the root of the repository.
2. Visual, commented Python code.
3. There is no need to read framework internals to understand flow.
4. Local smoke test is stable.
5. There is expected output proof and verification instructions.
6. Updated docs routes and `docs/DOCS_BACKLOG.md`.

## 11. Risks and Mitigations

1. Risk: examples will again become API wrappers.
- Mitigation: review checklist prohibits transport-only implementation as primary path.
2. Risk: complex setup will worsen onboarding.
- Mitigation: mandatory deterministic mode.
3. Risk: examples will become outdated relative to runtime.
- Mitigation: structure + smoke tests in CI.
4. Risk: duplication of logic between patterns.
- Mitigation: limited `shared/` layer + strict template contract.

## 12. Governance and Ownership

1. Any PR with `agent_examples/*` change updates:
   - `agent_examples/README.md`
- corresponding pattern `README.md`
   - `docs/DOCS_BACKLOG.md`
2. Before the merger, the following are required:
- local fast lane;
- verification of links/contracts;
- checking commands from docs.
