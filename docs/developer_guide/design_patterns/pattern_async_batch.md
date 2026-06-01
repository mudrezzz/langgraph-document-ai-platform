# Design Pattern: Async Batch

Update date: 2026-06-02
Status: Active

## 1. Goal

Process a set of independent document queries as one job with bounded chunk size and explicit partial-failure behavior.

This pattern is useful when the caller has a queue-like workload and needs one aggregated result instead of many single-query calls.

## 2. When to use

Use `async_batch` when:

1. You have N independent retrieval questions from the same case dataset.
2. You need item-level status (`completed` / `failed`) and batch summary counters.
3. You want deterministic in-process execution for local development and tests.

Do not use this pattern for:

1. Multi-step reviewer workflows (use `hitl_gate`).
2. Artifact authoring flow (use `authoring_first`).
3. Single-question retrieval UX (use `retrieval_first`).

## 3. Implementation map

- Pattern code:
  - `agent_examples/patterns/async_batch/agent.py`
  - `agent_examples/patterns/async_batch/workflow.py`
  - `agent_examples/patterns/async_batch/tools.py`
  - `agent_examples/patterns/async_batch/main.py`
- Runnable entrypoint:
  - `python agent_examples/run_example.py --pattern async_batch`

## 4. Contract shape

Input:

- `queries[]`
- `batch_size`
- `continue_on_error`
- `case_dataset_id`

Output:

- `batch_id`
- `total_queries`, `completed_queries`, `failed_queries`
- `average_confidence`
- `items[]` with:
  - `item_index`, `batch_index`, `query`
  - `status`
  - `confidence`, `evidence_blocks`
  - `top_sources[]`
  - `error` (only for failed items)

## 5. Verification

```bash
.venv/bin/pytest -q agent_examples/patterns/async_batch/tests/test_agent.py
.venv/bin/python agent_examples/patterns/async_batch/main.py
```

