# authoring_first - in-process artifact assembly

A minimal agent showing explicit authoring composition over framework/domain contracts
without HTTP transport: retrieval -> research -> draft -> review -> section authoring -> assembly.

---

## What it does

Builds a final artifact in one Python process:

1. runs retrieval workflow to collect evidence;
2. builds research summary and deterministic writer draft;
3. runs reviewer heuristics;
4. builds template-based section contracts;
5. generates section artifacts;
6. assembles and exports final document.

```text
Request
  -> RetrievalWorkflow.invoke()
  -> ResearchSummaryBuilder
  -> WriterDraftService
  -> SectionReviewService
  -> SectionAuthoringWorkflow (per section)
  -> DocumentAssemblyWorkflow
  -> Final artifact
```

---

## Architectural meaning

This is an **in-process** pattern: the agent imports framework/domain modules as a library
and executes everything in memory. No HTTP client and no backend runtime are required.

This is the recommended model for contributors who extend workflow logic directly.

---

## File structure

```text
authoring_first/
|- agent.py            # composition root and final response shaping
|- workflow.py         # explicit authoring pipeline orchestration
|- tools.py            # small helpers for context/steps/preview
|- config.py           # pattern config (dataset, mode, title, format)
|- prompts.py          # DEFAULT_QUERY
|- main.py             # direct entrypoint
|- expected_output/
|  |- result.example.json
|- tests/
|  |- test_agent.py
```

---

## Launch

Direct pattern run:

```bash
.venv/bin/python agent_examples/patterns/authoring_first/main.py
```

Through the general runner:

```bash
.venv/bin/python agent_examples/run_example.py --pattern authoring_first
```

Dry-run metadata check:

```bash
.venv/bin/python agent_examples/run_example.py --pattern authoring_first --dry-run
```

---

## Tests

```bash
.venv/bin/pytest -q agent_examples/patterns/authoring_first/tests/test_agent.py
```

---

## What to change first

1. `prompts.py` - change the business question.
2. `config.py` - switch `workflow_mode`, dataset, artifact title/format.
3. `workflow.py` - adjust section contract strategy or assembly behavior.
