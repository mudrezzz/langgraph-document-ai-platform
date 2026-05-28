# Design Patterns Library

Update date: 2026-05-29
Status: Active

This library is needed when a developer asks:

- “Which template should I choose for my script?”
- “What is the minimum working skeleton to take?”
- "how not to break framework contracts when expanding?"

Plan for replatform demo agents in in-process style:

- `docs/developer_guide/agent_examples_demo_program.md`

## How to use

1. Select a pattern for the task.
2. Run the linked runnable example from `agent_examples/run_example.py`.
3. Repeat the extension points structure for your case.
4. Test the changes via smoke/tests and update the docs backlog.

## Patterns catalog

1. Retrieval-First Agent  
When: you need a quick Q&A/evidence path based on documents.
Doc: `docs/developer_guide/design_patterns/pattern_retrieval_first.md`
Example: `agent_examples/patterns/retrieval_first/main.py` (in-process).

2. Authoring-First Agent  
When: you need a controlled process for generating the final artifact.
Doc: `docs/developer_guide/design_patterns/pattern_authoring_first.md`
Example: `agent_examples/run_example.py --pattern authoring_first`

3. HITL Gate Pattern  
When: you need a reviewer loop and a secure approve/rework path.
Doc: `docs/developer_guide/design_patterns/pattern_hitl_gate.md`
Example: `agent_examples/run_example.py --pattern hitl_gate --hitl-decisions needs_changes,approve`

Note on current status:

- `retrieval_first` and `authoring_first` are in-process patterns.
- `hitl_gate` remains API-driven while async reviewer flow is in transition.

## Checking

Quick test path:

```bash
.venv/bin/pytest -q agent_examples/tests/test_run_example.py
.venv/bin/pytest -q backend/tests/unit/test_agent_examples_contracts.py
.venv/bin/pytest -q backend/tests/unit/test_developer_guide_contracts.py
```
