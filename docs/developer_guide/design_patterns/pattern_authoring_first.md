# Pattern: Authoring-First Agent

When to use:

- you need to generate the final artifact (`report`, `brief`, `decision memo`);
- structured traceability and managed multi-step pipeline are important;
- there are rules for the format/quality of the final text.

## Skeleton

`retrieval -> draft -> reviewer (internal) -> assembly -> artifact`

## Runnable example

```bash
.venv/bin/python agent_examples/run_example.py --pattern authoring_first
```

## Extension points

1. Set up `workflow_mode` (`single_pass|multi_step`).
2. Add/edit artifact section structure template.
3. Connect an LLM provider through an env contract if necessary.

## Anti-patterns

1. Generate artifact without source traceability.
2. Mix orchestration with the API endpoint transport layer.
3. Break backward compatibility authoring payload contracts.
