# Quickstart

Update Date: 2026-05-29
Status: Entry point for new developers

This quickstart answers one question:
`I opened docs/developer_guide - what should I do next?`

## 1. 10-Minute Orientation

Read these first:

1. `docs/developer_guide/public_contract_surface.md`
2. `docs/developer_guide/framework_concepts.md`
3. `docs/developer_guide/examples_catalog.md`

After this, you should:

- understand what is stable vs experimental;
- see where framework vs application/domain/infra boundaries are;
- pick the closest example for your task.

## 2. Choose a Goal and Follow the Route

## Goal A: Extend existing functionality

1. Open `docs/developer_guide/extension_handbook.md`.
   Choose the extension type: `workflow | tool | MCP | persistence | domain`.
2. Open `docs/developer_guide/extension_recipes.md`.
   Pick the smallest viable change set and quality gate.
3. Verify interfaces as needed:
   - HTTP: `docs/developer_guide/api_reference.md`
   - MCP: `docs/developer_guide/mcp_reference.md`
4. After implementation:
   - update `docs/DOCS_BACKLOG.md`;
   - run docs contract checks:
     `.venv/bin/pytest -q backend/tests/unit/test_developer_guide_contracts.py`

## Goal B: Build a new agent flow quickly

In this project, an "agent" is typically:
`workflow + tools + optional API/MCP boundary`

Fast path:

1. `docs/developer_guide/framework_concepts.md`
   Align on runtime model (`BaseWorkflow`, async plane, HITL).
2. `docs/developer_guide/extension_handbook.md`
   Focus on `Workflow extension` and `Tool extension`.
3. `docs/framework_extension_guide.md`
   Validate framework constraints and extension hooks.
4. If an external interface is needed:
   - HTTP API: `docs/developer_guide/api_reference.md`
   - MCP tools: `docs/developer_guide/mcp_reference.md`
5. Bootstrap from runnable examples:
   - open `agent_examples/README.md`;
   - choose pattern `retrieval_first | authoring_first | hitl_gate`;
   - run `.venv/bin/python agent_examples/run_example.py --pattern <pattern>`.
6. Validate examples with unified harness:
   - `python agent_examples/tests/run_harness.py --lane fast`;
   - optional full lane: `python agent_examples/tests/run_harness.py --lane full`.
7. For reusable templates and extension points:
   - `docs/developer_guide/design_patterns/README.md`

## Goal C: Validate release path and operations

1. `docs/developer_guide/env_profile_snippets.md`
2. `docs/developer_guide/release_reproducible_flow.md`
3. `docs/developer_guide/operations_and_release.md`
4. `docs/developer_guide/observability_reference.md`

## 3. Role-Based Reading Shortcuts

- Integrator:
  `examples_catalog -> api_reference -> mcp_reference -> env_profile_snippets`
- Contributor:
  `framework_concepts -> extension_handbook -> extension_recipes -> adr_reading_map`
- Maintainer:
  `maintainer_playbook -> observability_reference -> release_reproducible_flow`

## 4. Runtime Bootstrap References

This quickstart is navigation-first.
For environment/bootstrap steps, use:

1. `docs/developer_guide/env_profile_snippets.md`
2. `docs/developer_guide/manual_demo_checks.md`
3. `backend/scripts/README.md`

## 5. Minimum Definition of Done for Your First Task

1. There is a working smoke/demo proof path.
2. Relevant docs are updated.
3. `docs/DOCS_BACKLOG.md` is updated.
