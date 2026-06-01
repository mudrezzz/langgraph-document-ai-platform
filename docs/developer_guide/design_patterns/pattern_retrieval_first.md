# Pattern: Retrieval-First Agent

When to use:

- we need a quick path “question -> evidence-based sampling”;
- the final output is an evidence pack, not a long authored artifact;
- explainability of sources and traceability to knowledge blocks are important.

## Skeleton

`build workflow -> invoke(state) -> evidence pack`

## Runnable example

```bash
.venv/bin/python agent_examples/patterns/retrieval_first/main.py
```

or

```bash
.venv/bin/python agent_examples/run_example.py --pattern retrieval_first
```

## Extension points

1. Change retrieval query via `prompts.py` or `main.py --query`.
2. Connect your case dataset via `main.py --dataset-id`.
3. Change filters in `agent_examples/patterns/retrieval_first/tools.py`.

## Anti-patterns

1. Do heavy authoring in the retrieval path.
2. Bypass typed contracts from `schemas`.
3. Ignore task events and observability after expansion.
