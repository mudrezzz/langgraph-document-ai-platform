# Documentation Backlog (Framework)

Start Date: 2026-04-30  
Last Update: 2026-05-29  
Status: Active (living document)

## Purpose

This backlog is the single source of truth for framework-layer developer documentation tasks.

## Freshness Rule (Required)

1. Every documentation change must update this file.
2. Any documentation scope change (new guide, new reference, new policy) must be tracked as a new task.
3. When a task is closed, always update:
   - `Status`
   - `Last Update`
   - short `Notes` summary (what exactly was completed).
4. A docs pull request is considered incomplete if `docs/DOCS_BACKLOG.md` is not updated.

## Statuses

- `Planned`
- `In Progress`
- `Blocked`
- `Done`

## Backlog

| ID | Priority | Workstream | Task | Deliverable | Status | Last Update | Notes |
|---|---|---|---|---|---|---|---|
| DOC-001 | P0 | Information Architecture | Create a single docs entrypoint for the Integrator/Contributor/Maintainer roles | New index of structure and reading routes | Done | 2026-04-30 | Updated `docs/developer_guide/README.md`: added role-based entrypoint and reading routes for Integrator/Contributor/Maintainer. |
| DOC-002 | P0 | Public Contracts | Commit Public Contract Surface v1 (stable/experimental) | Document with boundaries of stability | Done | 2026-04-30 | Added `docs/developer_guide/public_contract_surface.md` with stable/experimental/internal matrix for API, MCP, schemas and runtime config. |
| DOC-003 | P0 | Framework Concepts | Describe framework layers and execution model (LangGraph runtime, async plane, HITL, quality gates) | Concept guide | Done | 2026-04-30 | Added `docs/developer_guide/framework_concepts.md` with layer map, runtime model, async plane, HITL and quality gates. |
| DOC-004 | P0 | Onboarding | Prepare quickstart profiles: local dev / stage-like / prod-like | Advanced onboarding guide | Done | 2026-04-30 | `quickstart.md` has been reworked into a HOW TO entrypoint according to the developer's goals (extension, quick start of a new agent flow, release path), runtime profiles have been moved to `env_profile_snippets.md`. |
| DOC-005 | P0 | End-to-End | Add canonical walkthrough: documents -> indexing -> retrieval -> authoring -> HITL -> artifact | End-to-end practical guide | Done | 2026-04-30 | Added `docs/developer_guide/canonical_e2e_walkthrough.md`; guide is linked to `developer_guide/README.md` for the Integrator path. |
| DOC-006 | P0 | API Reference | Generate a human-readable reference using FastAPI endpoints + payload contracts | API reference guide | Done | 2026-04-30 | Added `docs/developer_guide/api_reference.md` (endpoint groups, payload contracts, auth headers, error mapping). |
| DOC-007 | P0 | MCP Reference | Create a reference for MCP services/tools/scopes/roles/errors | MCP reference guide | Done | 2026-04-30 | Added `docs/developer_guide/mcp_reference.md` with service/tool ​​matrix, scopes, required roles and error semantics. |
| DOC-008 | P0 | Env & Config | Create a single directory of env variables and runtime effects | Configuration reference | Done | 2026-04-30 | Added `docs/developer_guide/env_config_reference.md` with runtime env catalog and profile effects. |
| DOC-009 | P0 | Ops & Release | Package the smoke/release gate process as one reproducible flow | Operations + release playbook sync | Done | 2026-04-30 | Added `docs/developer_guide/release_reproducible_flow.md`; updated `operations_and_release.md` and entrypoint links. |
| DOC-010 | P0 | Extension Path | Detail extension handbooks: workflow/tool/MCP/persistence/domain | Extension documentation set | Done | 2026-04-30 | Added `docs/developer_guide/extension_handbook.md` with playbooks for workflow/tool/MCP/persistence/domain extension. |
| DOC-011 | P1 | Persistence & Data | Describe the database model: migrations, latest/history policy, version lookup, rollback expectations | Persistence reference | Done | 2026-04-30 | Added `docs/developer_guide/persistence_reference.md` with data model map, migration policy, version lookup and rollback expectations. |
| DOC-012 | P1 | Observability | Describe task events/observability/HITL observability and SLA interpretation | Observability handbook | Done | 2026-04-30 | Added `docs/developer_guide/observability_reference.md` with endpoint map, metrics and SLA interpretation rules. |
| DOC-013 | P1 | Governance | Prepare OSS governance docs: CONTRIBUTING, CODE_OF_CONDUCT, SUPPORT | Governance package | Done | 2026-04-30 | Added `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `SUPPORT.md`. |
| DOC-014 | P1 | Security | Prepare SECURITY policy (vuln reporting, disclosure flow, RBAC limitations) | SECURITY.md | Done | 2026-04-30 | Added `SECURITY.md` with disclosure flow, scope and RBAC limitations. |
| DOC-015 | P1 | Versioning | Fix the documentation/contractual versioning policy and deprecation policy | Versioning policy doc | Done | 2026-04-30 | Added `docs/developer_guide/versioning_policy.md` with stable/experimental deprecation and contract versioning rules. |
| DOC-016 | P1 | QA for Docs | Enter docs contract checks for new sections and required links | Unit tests for docs contracts | Done | 2026-04-30 | Updated `backend/tests/unit/test_developer_guide_contracts.py`: checking new mandatory guide pages and baseline checks for `docs/DOCS_BACKLOG.md`. |
| DOC-017 | P2 | Examples Catalog | Directory of reusable examples for integrators (retrieval-first, authoring-first, MCP-first) | Examples cookbook | Done | 2026-04-30 | Added `docs/developer_guide/examples_catalog.md` with retrieval-first/authoring-first/MCP-first/canonical scripts. |
| DOC-018 | P2 | Architecture Decision Navigation | Add “ADR reading map” for external developers | ADR navigation guide | Done | 2026-04-30 | Added `docs/developer_guide/adr_reading_map.md` with role-based fast path and topic map for ADR. |
| DOC-019 | P2 | Maintainer Playbook | Describe the process for docs releases, triage docs issues, review rules | Maintainer docs playbook | Done | 2026-04-30 | Added `docs/developer_guide/maintainer_playbook.md` with intake/triage/review/release cadence and DoD for docs PR. |
| DOC-020 | P0 | License | Define and commit OSS license + rationale | LICENSE + short rationale doc | Done | 2026-04-30 | Added `LICENSE` (Apache-2.0) and `docs/oss_license_rationale.md`. |
| DOC-021 | P1 | Onboarding Ergonomics | Add profile-ready env snippets/templates (dev/stage/prod) for a quick start without manually searching for variables | Env snippets guide/template | Done | 2026-04-30 | Added `docs/developer_guide/env_profile_snippets.md` with copy-paste `dev/stage/prod` profiles and recommended smoke commands. |
| DOC-022 | P0 | Repository Front Door | Rewrite main README as GitHub entrypoint (value proposition + CTA + shortcuts) | Marketing-oriented root README | Done | 2026-04-30 | `README.md` has been completely redesigned: short product pitch, usage scenarios, 5-minute quickstart and routes in `docs/developer_guide/*`; payload contracts have been moved to `api_reference.md`. |
| DOC-023 | P0 | Agent Builder Onboarding | Add a quick HOW TO to the root README for the “create a new agent/agent flow” scenario + extension map | README quickstart extension block | Done | 2026-04-30 | Sections `Quickstart: Build A New Agent Flow` and `Extension Map` with direct routes to `framework_concepts`, `extension_handbook`, `extension_recipes`, `api_reference`, `mcp_reference`, `persistence_reference` have been added to `README.md`. |
| DOC-024 | P0 | README Conversion | Add to README copy-paste starters (retrieval-first/authoring-first) and a short architecture story for non-technical visitors | README starter commands + value framing block | Done | 2026-04-30 | Added `Copy-Paste Starters` and `30-Second Architecture Story` with value claims (speed/risk/ownership) and direct start commands to `README.md`. |
| DOC-025 | P0 | Example Gallery | Add a runnable library of simple framework cases for quick inspiration and start | `backend/examples` quickstart launcher + examples guide | Done | 2026-04-30 | Added `backend/examples/quickstart_agents.py` and `backend/examples/README.md` with runnable cases `retrieval_faq_assistant`, `authoring_policy_brief`, `hitl_review_loop`, support for `--list`, `dry-run` and `--execute`. |
| DOC-026 | P0 | Pattern Library | Add the design patterns library with links to runnable examples and tests | `docs/developer_guide/design_patterns/*` + unit/docs contracts | Done | 2026-04-30 | Added `design_patterns/README.md` and pattern-guides (`retrieval-first`, `authoring-first`, `hitl-gate`), updated `README.md`/`developer_guide/README.md`, added unit test `test_example_quickstart_agents.py` and extended docs contracts. |
| DOC-027 | P0 | Productized Agent Examples | Rebuild examples as a separate product-like directory of Python agents without having to read framework internals | `agent_examples/*` (single-folder entrypoint, pattern code, tests) | Done | 2026-04-30 | Added a new directory `agent_examples/` with a single runner `run_example.py`, a common runtime/client binding, three pattern folders (`retrieval_first`, `authoring_first`, `hitl_gate`) and local tests. |
| DOC-028 | P0 | Example UX Integration | Embed new `agent_examples` into the main onboarding and README positioning of the project | README + developer guide route updates + contracts | Done | 2026-04-30 | Updated `README.md`, `docs/developer_guide/README.md`, `quickstart.md`, `examples_catalog.md`, `design_patterns/*`; added contract/unit tests for structure and dry-run launch of `agent_examples`. |
| DOC-029 | P0 | Agent Examples Replatform Plan | Record a detailed plan for the transition of demo agents to in-process framework usage (instead of transport-first examples) | Program roadmap doc + docs route integration | Done | 2026-04-30 | Added `docs/developer_guide/agent_examples_demo_program.md`; updated `developer_guide/README.md`, `design_patterns/README.md`, docs contracts. |
| DOC-030 | P0 | Retrieval Pattern Rebuild | Rebuild `retrieval_first` as library-style in-process agent (`main.py + workflow.py + tools.py`) | Reworked retrieval pattern folder + tests + expected output | Done | 2026-04-30 | `retrieval_first` moved to direct `build_retrieval_workflow(...).invoke(...)`; added `main.py`, `workflow.py`, `tools.py`, `expected_output`, pattern tests and updated `run_example.py` to in-process execution model for retrieval. |
| DOC-031 | P0 | Authoring Pattern Rebuild | Rebuild `authoring_first` as an in-process agent with an explicit artifact assembly model | Reworked authoring pattern folder + tests + expected output | Done | 2026-05-29 | Closed Slice 34.1.1: `authoring_first` moved to in-process composition (`main.py + workflow.py + tools.py`), added pattern tests and expected output proof, synchronized runner/docs for execution-model consistency, and preserved CLI entrypoint compatibility (`run_example.py --pattern authoring_first`). |
| DOC-032 | P0 | HITL Pattern Rebuild | Rebuild `hitl_gate` as an in-process pattern with reviewer loop contract | Reworked hitl pattern folder + tests + expected output | Done | 2026-05-29 | Closed Slice 34.2.1: `hitl_gate` moved to in-process reviewer loop (`main.py + workflow.py + tools.py`), added pattern tests and expected output proof, updated runner/docs status, and preserved CLI entrypoint compatibility (`run_example.py --pattern hitl_gate`). |
| DOC-033 | P0 | Examples Test Harness | Add unified fast/full test lanes for `agent_examples` (structure/unit/smoke) | Test matrix doc + CI-ready command set | Done | 2026-05-29 | Closed Slice 34.3.1: added unified harness `agent_examples/tests/run_harness.py` with `fast/full` lanes and optional external-LLM smoke gating; synced docs routes and contracts. |
| DOC-034 | P1 | Async Batch Pattern | Add a separate in-process demo pattern for batch/long-running scenarios | `patterns/async_batch/*` + docs/tests | Planned | 2026-04-30 | After stabilization of the three basic P0 patterns. |
| DOC-035 | P1 | MCP Facade Pattern | Add a separate demo pattern `agent as MCP tools` on top of the core agent logic | `patterns/mcp_tool_facade/*` + docs/tests | Planned | 2026-04-30 | Should show the separation of core logic and MCP transport adapter. |
| DOC-036 | P0 | OSS Program Planning | Fix a single improvement program contributor funnel with iterations and slices | `docs/developer_guide/oss_contributor_funnel_program.md` + sync links | Done | 2026-05-28 | Closed Slice 33.8.1: program moved to operational format (iteration register + slice DoD + KPI baseline), synced links in `README.md` and `CONTRIBUTING.md`, and aligned policy wording for AI-assisted contribution semantics. |
| DOC-037 | P0 | Packaging Integrity | Synchronize package license/readme metadata with OSS policy repository | `backend/packages/pyproject.toml` + `backend/packages/README.md` | Done | 2026-05-26 | Closed Slice 33.1.1 and 33.1.2: package license metadata aligned (`Apache-2.0`), added package-level README under `readme = \"README.md\"`. |
| DOC-038 | P0 | README No-Infra Entry | Add no-infra first-success path and expected output to root README | `README.md` update (2-minute demo + output proof) | Done | 2026-05-26 | Added `2-Minute Demo: No Docker, No Postgres` block with dry-run/execute commands, explicit no-infra scope and expected output; The production smoke path is left below. |
| DOC-039 | P0 | First-Time Contributor Path | Add a first-time contributor section and clear out links in the contribution flow | `CONTRIBUTING.md` update | Done | 2026-05-26 | Added `First-time contributors` section, described the safe path of the first PR, added docs/examples/packaging-only check profile, fixed the link to `docs/developer_guide/mcp_reference.md`. |
| DOC-040 | P1 | Community Templates | Introduce issue forms and PR template for structured intake | `.github/ISSUE_TEMPLATE/*` + `.github/pull_request_template.md` | Done | 2026-05-26 | Added issue forms (`bug_report`, `documentation`, `feature_request`, `question`) and PR template with type/test/contract/checklist sections. |
| DOC-041 | P1 | Public Backlog Funnel | Prepare the starting public issue backlog and label taxonomy | 15-20 issue drafts + label matrix + triage policy note | Done | 2026-05-27 | Slice 33.2.2 and 33.2.3 are closed: label taxonomy is applied, triage baseline is documented, 16 public issues (#1-#16) have been created, >=8 of them are marked `good first issue`. |
| DOC-042 | P2 | README Front Door v2 | Rebuild README for open-source front door and add comparison table | `README.md` restructure + use-case matrix | Done | 2026-05-27 | README rebuilt in front-door order: `Who is this for` -> `When not to use` -> `2-Minute Demo` -> `Example Output` -> `What You Can Build` -> `Architecture` -> `Production Smoke` -> `Documentation Map` -> `Contributing` -> `License`. |
| DOC-043 | P2 | Discoverability | Synchronize GitHub topics and positioning capabilities | Repository topics + docs notes | Done | 2026-05-27 | The repository uses topics on actual capabilities: `langgraph`, `document-ai`, `rag`, `mcp`, `human-in-the-loop`, `pgvector`, `fastapi`, `celery`, `openrouter`, `ai-agents`, `document-processing`, `retrieval-augmented-generation`, `pdf-processing`, `workflow-automation`. |
| DOC-044 | P2 | Contributor Motivation & Feedback Loop | Add a motivational and feedback circuit for external contributors | README/CONTRIBUTING messaging + `FEEDBACK.md` + project update template | Done | 2026-05-28 | Closed Slice 33.4.1/33.4.2/33.4.3: motivation and AI-assisted policy in README/CONTRIBUTING plus `FEEDBACK.md` and `docs/project_update_template.md` integrated into support/contributor routes. |
| DOC-045 | P0 | Documentation Language Baseline | Translate primary contributor-facing docs to English and remove mojibake in governance/front-door files | English-first `README/CONTRIBUTING/CODE_OF_CONDUCT/SUPPORT` + synced `docs/DOCS_BACKLOG.md` notes | Done | 2026-05-28 | Completed full translation slices for contributor-facing documentation surface (root governance/front-door docs, `docs/developer_guide/*`, `agent_examples/*`, `backend/examples/*`, `backend/scripts/README.md`) with mojibake cleanup and docs-contract test pass. |
| DOC-046 | P1 | Vibe-Coder Agent Bootstrap | Add a GitHub-based skill import workflow for popular AI coding agents | `import_agent_skill.py` + tests + guide + docs links | Done | 2026-05-28 | Added `backend/scripts/import_agent_skill.py` (codex/claude/cursor presets, GitHub URL/repo-path modes, markdown/host/size safety guards), unit tests, and contributor-facing docs (`vibecoder_skill_import.md`) with README/CONTRIBUTING/scripts-guide integration. |

## Backlog Change Log

- 2026-05-29: Closed DOC-033 / Slice 34.3.1 (examples test harness): added `agent_examples/tests/run_harness.py`, documented fast/full lane matrix in `docs/developer_guide/agent_examples_test_harness.md`, and linked harness commands from README/quickstart/agent examples docs.
- 2026-05-29: Closed DOC-032 / Slice 34.2.1 (hitl_gate in-process replatform): implemented in-process reviewer loop with `needs_changes -> approve` contract, added tests and expected output, and synchronized docs/runner messaging.
- 2026-05-29: Closed DOC-031 / Slice 34.1.1 (authoring-first in-process replatform): updated `agent_examples/patterns/authoring_first/*` to explicit in-process artifact assembly flow, added tests and expected output, and synced design/docs references.
- 2026-05-28: Closed DOC-036 / Slice 33.8.1 (program operationalization): updated `docs/developer_guide/oss_contributor_funnel_program.md` to `In Progress` operational state with iteration tracker, slice-level DoD, and KPI baseline; synced front-door links in `README.md` and `CONTRIBUTING.md`.
- 2026-05-28: Closed DOC-044 / Slice 33.4.3: added `FEEDBACK.md` and `docs/project_update_template.md`, linked them from `README.md`, `CONTRIBUTING.md`, `SUPPORT.md`, and `docs/developer_guide/README.md`.
- 2026-05-28: Closed DOC-046 / Slice 33.7.1 (vibe-coder agent bootstrap): added `backend/scripts/import_agent_skill.py`, unit tests `backend/tests/unit/test_import_agent_skill_script.py`, new guide `docs/developer_guide/vibecoder_skill_import.md`, and linked it from README/CONTRIBUTING/developer guide/scripts guide.
- 2026-05-28: Slice 33.6.2 completed (contract/link integrity audit): relative markdown links validated (`BROKEN_COUNT=0`), docs contract tests passed, and policy wording normalized in `SECURITY.md`, `api_reference.md`, `mcp_reference.md`, `public_contract_surface.md`.
- 2026-05-28: Slice 33.6.1 completed (editorial QA pass): manually polished front-door docs (`README.md`, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `SUPPORT.md`, `docs/developer_guide/README.md`, `docs/developer_guide/quickstart.md`) and aligned terminology.
- 2026-05-28: Closed DOC-045 (all planned translation slices). Contributor-facing documentation surface is now English-first and mojibake-clean.
- 2026-05-28: Started DOC-045 / Slice 33.5.1 (English language baseline for contributor-facing docs); focus files: `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `SUPPORT.md`, and backlog sync.
- 2026-05-28: Slice 33.5.1 continued - translated `docs/developer_guide/README.md` to English and normalized quote/dash encoding in `README.md`.

- 2026-05-28: Closed Slice 33.4.2 under DOC-044; AI-assisted contribution policy was fixed (without financial \"tokens\", without pay-to-prioritize semantics).
- 2026-05-27: The scope of DOC-044 has been clarified: an explicit motivation/progression path for vibe-coders has been added to README/CONTRIBUTING within the framework of existing governance/checks.
- 2026-05-27: DOC-044 moved to `In Progress`; Slice 33.4.1 is closed (motivation copy in README/CONTRIBUTING), the remaining scope is left at Slice 33.4.2/33.4.3.
- 2026-05-27: Closed DOC-043; capability-aligned topics (14 pieces, <=20) have been added to the GitHub repository.
- 2026-05-27: Added scope DOC-042: a comparison/use-case table for early qualification of scripts was added to the root README.
- 2026-05-27: Closed DOC-042; root README rebuilt for front-door onboarding flow (no-infra success path to production smoke path, explicit docs map and contributor navigation).
- 2026-05-27: Closed DOC-041; an initial public backlog of 16 issues (`#1..#16`) was created with a new label taxonomy, including `good first issue` for newcomer-friendly issues.
- 2026-05-27: DOC-041 moved to `In Progress`; Slice 33.2.2 is closed (labels + triage baseline), pending scope has been moved to Slice 33.2.3 (initial public issue backlog).
- 2026-05-26: Closed DOC-040; added `.github/ISSUE_TEMPLATE/*` and `.github/pull_request_template.md` for structured issue/PR intake.
- 2026-05-26: Closed DOC-039; updated `CONTRIBUTING.md` (first-time contributor path, link consistency, docs/examples/packaging-only checks).
- 2026-05-26: Closed DOC-038; no-infra demo entrypoint and expected output are added to the root README, production smoke path is saved as a separate block below.
- 2026-05-26: Closed DOC-037; Slice 33.1.1 (license alignment) and Slice 33.1.2 (`backend/packages/README.md`) have been completed.
- 2026-05-26: DOC-037 moved to `In Progress`; Slice 33.1.1 is closed (package license metadata -> Apache-2.0), the remaining scope is opened according to the package README.
- 2026-05-26: Added planned tasks DOC-036..DOC-044 for Increment 33 (OSS contributor funnel); a program document `docs/developer_guide/oss_contributor_funnel_program.md` has been created; `Last Update` has been updated.
- 2026-04-30: Closed DOC-030; `retrieval_first` has been moved to an in-process framework pattern with separate `main.py`, workflow/tools and local tests.
- 2026-04-30: Added and closed DOC-029 (detailed roadmap of replatform demo agents in in-process style); added planned tasks DOC-030..DOC-035.
- 2026-04-30: DOC-027 and DOC-028 closed; a new product-style directory `agent_examples/` has been introduced and integrated as the main entrypoint for python agent examples.
- 2026-04-30: DOC-025 and DOC-026 closed; added runnable examples gallery, design patterns library and tests/contracts for new entrypoints.
- 2026-04-30: Closed DOC-024; copy-paste starters and 30-second architecture story with value framing have been added to the README.
- 2026-04-30: Closed DOC-023; A quick path for the new agent flow and a map of extension types have been added to the root README.
- 2026-04-30: Closed DOC-022; The root `README.md` has been rewritten into the GitHub showcase format and synchronized with the developer guide.
- 2026-04-30: Updated DOC-004 notes; `quickstart.md` has been redesigned into a navigation HOW TO for the developer.
- 2026-04-30: DOC-017, DOC-018 and DOC-019 are closed; added examples catalog, ADR reading map and maintainer docs playbook.
- 2026-04-30: Closed DOC-021; added env snippets guide for `dev/stage/prod`.
- 2026-04-30: DOC-015 and DOC-016 closed; added versioning policy and docs contract checks.
- 2026-04-30: Closed DOC-020; Apache-2.0 and rationale license is fixed.
- 2026-04-30: Closed DOC-013 and DOC-014; governance and security policy documents have been added.
- 2026-04-30: Closed DOC-012; observability handbook added.
- 2026-04-30: Closed DOC-011; added persistence/data reference.
- 2026-04-30: Closed DOC-010; added extension handbook on key types of extensions.
- 2026-04-30: Closed DOC-009; added reproducible release flow guide.
- 2026-04-30: Closed DOC-007 and DOC-008; added `mcp_reference.md` and `env_config_reference.md`.
- 2026-04-30: Added DOC-021 (profile-ready env snippets/templates) as a new onboarding scope.
- 2026-04-30: Closed DOC-006; added API reference according to FastAPI boundary.
- 2026-04-30: Closed DOC-005; added end-to-end practical walkthrough `documents -> indexing -> retrieval -> authoring -> HITL -> artifact`.
- 2026-04-30: Closed DOC-004; quickstart extended with local dev/stage-like/prod-like profiles.
- 2026-04-30: Closed DOC-003; added `framework_concepts.md` and updated learning path in `developer_guide/README.md`.
- 2026-04-30: Closed DOC-001 and DOC-002; added role-based docs entrypoint and `public_contract_surface.md` (v1).
- 2026-04-30: Initialized baseline backlog for full cycle framework documentation and OSS readiness.

