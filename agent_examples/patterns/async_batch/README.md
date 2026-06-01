# async_batch - in-process batched retrieval

Pattern for long-running style workloads where multiple queries are processed in bounded chunks.

This demo stays in-process and executes framework workflows directly in Python.

## What it shows

1. One batch run with multiple query items.
2. Chunked execution by `batch_size`.
3. Partial-failure behavior (`continue_on_error`).
4. Aggregated output (`completed_queries`, `failed_queries`, `average_confidence`).

## Run

Default sample queries:

```bash
.venv/bin/python agent_examples/patterns/async_batch/main.py
```

Custom queries from CLI:

```bash
.venv/bin/python agent_examples/patterns/async_batch/main.py \
  --query "What release controls are mandatory?" \
  --query "What unresolved risks remain?"
```

Load a query list from JSON:

```bash
.venv/bin/python agent_examples/patterns/async_batch/main.py \
  --queries-file agent_examples/patterns/async_batch/sample_input/queries.json
```

Run through the general runner:

```bash
.venv/bin/python agent_examples/run_example.py --pattern async_batch
```

Dry-run note:

```bash
.venv/bin/python agent_examples/run_example.py --pattern async_batch --dry-run
```

## Output proof

Reference payload:

- `agent_examples/patterns/async_batch/expected_output/result.example.json`

## Tests

```bash
.venv/bin/pytest -q agent_examples/patterns/async_batch/tests/test_agent.py
```

