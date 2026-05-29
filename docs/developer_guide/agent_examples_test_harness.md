# Agent Examples Test Harness

Update Date: 2026-05-29  
Status: Active

This page defines the unified test lanes for `agent_examples`.

Single entrypoint:

`agent_examples/tests/run_harness.py`

## 1. Fast Lane

Use for local iteration and PR pre-check on pattern logic/contracts.

Command:

```bash
python agent_examples/tests/run_harness.py --lane fast
```

Included checks:

1. `agent_examples/patterns/retrieval_first/tests/test_agent.py`
2. `agent_examples/patterns/authoring_first/tests/test_agent.py`
3. `agent_examples/patterns/hitl_gate/tests/test_agent.py`
4. `agent_examples/tests/test_run_example.py`
5. `backend/tests/unit/test_agent_examples_contracts.py`

## 2. Full Lane

Use for deeper validation, including optional external-LLM smoke for `device_search`.

Command:

```bash
python agent_examples/tests/run_harness.py --lane full
```

Behavior:

- always runs all checks from Fast Lane;
- runs `device_search` smoke if:
  - `RUN_EXTERNAL_LLM_TESTS=1`, and
  - `OPENROUTER_API_KEY` is set.
- otherwise prints explicit skip message and still succeeds.

## 3. Full Lane With Required External Smoke

Use this when CI policy requires `device_search` smoke.

```bash
RUN_EXTERNAL_LLM_TESTS=1 OPENROUTER_API_KEY=... \
python agent_examples/tests/run_harness.py --lane full --require-external-llm-smoke
```

Optional override:

```bash
python agent_examples/tests/run_harness.py --lane full --run-external-llm-smoke
```

## 4. Why this split

1. Keep routine contributor checks fast and deterministic.
2. Preserve a production-like path for LLM-backed smoke when credentials are available.
3. Prevent accidental regressions in example contracts and entrypoints.
