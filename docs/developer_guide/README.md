# External Developer Guide

Update Date: 2026-05-29
Status: Active

This section is the single entry point for external developers who want to use the backend/framework library as a production retrieval + authoring platform on LangGraph.

## 1. Role-Based Entrypoint

Unified reading path by role:

1. Integrator:
   - `docs/developer_guide/quickstart.md`
   - `agent_examples/README.md`
   - `docs/developer_guide/design_patterns/README.md`
   - `docs/developer_guide/agent_examples_test_harness.md`
   - `docs/developer_guide/env_profile_snippets.md`
   - `docs/developer_guide/manual_demo_checks.md`
   - `docs/developer_guide/canonical_e2e_walkthrough.md`
   - `docs/developer_guide/examples_catalog.md`
   - `docs/developer_guide/api_reference.md`
   - `docs/developer_guide/mcp_reference.md`
   - `docs/developer_guide/env_config_reference.md`
   - `docs/developer_guide/public_contract_surface.md`
2. Contributor (framework/domain extension):
   - `docs/developer_guide/framework_concepts.md`
   - `docs/developer_guide/agent_examples_demo_program.md`
   - `docs/developer_guide/design_patterns/README.md`
   - `docs/developer_guide/design_patterns/pattern_retrieval_first.md`
   - `docs/developer_guide/design_patterns/pattern_authoring_first.md`
   - `docs/developer_guide/design_patterns/pattern_hitl_gate.md`
   - `docs/developer_guide/design_patterns/pattern_async_batch.md`
   - `docs/developer_guide/design_patterns/pattern_mcp_tool_facade.md`
   - `docs/developer_guide/agent_examples_test_harness.md`
   - `docs/developer_guide/api_reference.md`
   - `docs/developer_guide/mcp_reference.md`
   - `docs/developer_guide/env_config_reference.md`
   - `docs/developer_guide/env_profile_snippets.md`
   - `docs/developer_guide/persistence_reference.md`
   - `docs/developer_guide/observability_reference.md`
   - `docs/developer_guide/versioning_policy.md`
   - `docs/developer_guide/adr_reading_map.md`
   - `docs/developer_guide/extension_handbook.md`
   - `docs/developer_guide/public_contract_surface.md`
   - `docs/developer_guide/extension_recipes.md`
   - `docs/developer_guide/vibecoder_skill_import.md`
   - `docs/framework_extension_guide.md`
3. Maintainer (runtime/release):
   - `docs/developer_guide/persistence_reference.md`
   - `docs/developer_guide/observability_reference.md`
   - `docs/developer_guide/versioning_policy.md`
   - `docs/developer_guide/maintainer_playbook.md`
   - `docs/developer_guide/operations_and_release.md`
   - `docs/developer_guide/release_reproducible_flow.md`
   - `docs/developer_guide/oss_contributor_funnel_program.md`
   - `CONTRIBUTING.md`
   - `FEEDBACK.md`
   - `docs/project_update_template.md`
   - `CODE_OF_CONDUCT.md`
   - `SUPPORT.md`
   - `SECURITY.md`
   - `LICENSE`
   - `docs/production_runbook.md`
   - `backend/scripts/README.md`

## 2. What Is Considered a Stable Public Contract

- FastAPI endpoints in `backend/apps/api` and their payload contracts in `docs/developer_guide/api_reference.md`.
- Framework extension path in `docs/framework_extension_guide.md`.
- Production runtime path in `docs/production_runbook.md`.
- Release acceptance scripts in `backend/scripts/*`.
- Versioned stable/experimental matrix in `docs/developer_guide/public_contract_surface.md`.

## 3. What This Guide Does Not Replace

- It does not replace the architecture overview: `docs/architecture/System_Architecture_Overview.md`.
- It does not replace architecture decision history (ADR): `docs/adr/README.md`.
- It does not replace the detailed manual smoke runbook: `docs/manual_smoke_postgres_runbook.md`.

## 4. Recommended Learning Path for New Developers

1. `quickstart.md`: choose a goal-based route (extension, new agent, release path).
2. `public_contract_surface.md`: lock stable/experimental boundaries before changes.
3. `framework_concepts.md`: align on execution model (runtime, async plane, HITL, quality gates).
4. `canonical_e2e_walkthrough.md`: walk the full path `documents -> indexing -> retrieval -> authoring -> HITL -> artifact`.
5. `agent_examples/README.md`: choose a runnable Python agent example and run it with `run_example.py`.
6. `agent_examples_demo_program.md`: align with the target in-process demo-agent model and roadmap.
7. `design_patterns/README.md`: choose a pattern for your use case and extension points.
8. `agent_examples_test_harness.md`: run unified fast/full lanes for example contracts and smoke.
9. `api_reference.md`: verify endpoints, payload contracts, and error mapping.
10. `mcp_reference.md`: verify MCP tools/scopes/roles and error semantics.
11. `env_config_reference.md`: define the env profile before run or deploy.
12. `env_profile_snippets.md`: copy a ready-to-use env profile (`dev/stage/prod`).
13. `persistence_reference.md`: verify tables, version policy, and rollback expectations.
14. `observability_reference.md`: interpret task/HITL observability and SLA aggregates.
15. `versioning_policy.md`: verify deprecation and contract versioning rules.
16. `examples_catalog.md`: choose the closest reusable integration scenario.
17. `manual_demo_checks.md`: validate canonical indexing and real PDF/PPTX parsing path.
18. `adr_reading_map.md`: follow ADR path by role and change topic.
19. `extension_handbook.md`: choose the required extension playbook (workflow/tool/MCP/persistence/domain).
20. `extension_recipes.md`: add your workflow/tool/MCP path based on current framework contracts.
21. `vibecoder_skill_import.md`: import/update local `SKILL.md/AGENT.md` from GitHub for codex/claude/cursor.
22. `maintainer_playbook.md`: verify docs release/triage/review rules.
23. `release_reproducible_flow.md`: run the linear reproducible release path.
24. `operations_and_release.md`: run the release decision gate as the final quality barrier.
