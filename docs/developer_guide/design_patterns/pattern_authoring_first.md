# Pattern: Authoring-First Agent

When to use:

- you need to generate the final artifact (`report`, `brief`, `decision memo`);
- structured traceability and managed multi-step pipeline are important;
- there are rules for the format/quality of the final text.

## Skeleton

`retrieval -> research -> draft -> reviewer -> section authoring -> assembly -> artifact`

## Runnable example

```bash
.venv/bin/python agent_examples/patterns/authoring_first/main.py
```

## Extension points

1. Configure `workflow_mode` (`single_pass|multi_step`) and `artifact_format`.
2. Extend section-contract strategy in `workflow.py` (`template_id`, selection rules).
3. Customize deterministic writer/review/assembly behavior with domain services.

## Anti-patterns

1. Generate artifact without source traceability.
2. Hide orchestration behind API transport wrappers in an in-process example.
3. Break backward compatibility authoring payload contracts.
