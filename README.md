# LangGraph Document AI Platform

Production-oriented platform for document-centric AI agents on top of LangGraph.

Build retrieval, indexing, authoring, and human-in-the-loop review flows with auditable task lifecycle, typed contracts, and release gates.

## Why This Project

- End-to-end document AI flow in one stack: `ingest -> index -> retrieve -> author -> review -> artifact`.
- Production-first runtime: PostgreSQL + pgvector, async execution plane (Celery/Redis), release gate orchestration.
- Auditable by design: task history, task events, observability summaries, HITL action timeline.
- Strong extension surface for teams: workflow/tool/MCP/persistence/domain playbooks.
- Clear public contract boundaries for integrators and contributors.

## What You Can Build

1. Retrieval-first assistant with canonical knowledge indexing and evidence packs.
2. Authoring copilot with multi-step draft flow and iterative HITL review loop.
3. Governance-aware template/repository/artifact services over MCP.

## 5-Minute Quickstart (Linux)

Requirements:

- `python` 3.12+
- `docker` + `docker compose`
- `curl`

Quick smoke path:

```bash
bash backend/scripts/postgres_up.sh
bash backend/scripts/postgres_migrate.sh
bash backend/scripts/smoke_retrieval_api.sh --port 8010
```

Stop local PostgreSQL:

```bash
bash backend/scripts/postgres_down.sh --remove-volumes
```

For profile-ready env snippets (`dev/stage/prod`) and complete smoke matrix, use:

- `docs/developer_guide/env_profile_snippets.md`
- `backend/scripts/README.md`

## Quickstart: Build A New Agent Flow

This project treats an "agent" as:

`workflow + tools + optional API/MCP boundary`

Minimal path:

1. Start from architecture/constraints:
   - `docs/developer_guide/framework_concepts.md`
   - `docs/framework_extension_guide.md`
2. Pick a reusable blueprint:
   - `docs/developer_guide/examples_catalog.md`
3. Implement by playbook:
   - `docs/developer_guide/extension_handbook.md`
   - `docs/developer_guide/extension_recipes.md`
4. Wire external interface (if needed):
   - HTTP API: `docs/developer_guide/api_reference.md`
   - MCP tools: `docs/developer_guide/mcp_reference.md`
5. Verify and close:
   - run smoke path from `backend/scripts/README.md`
   - update docs and `docs/DOCS_BACKLOG.md`

Developer-oriented deep quickstart:

- `docs/developer_guide/quickstart.md`

## Choose Your Path

- I need fast orientation in docs and role-based map:
  - `docs/developer_guide/README.md`
  - `docs/developer_guide/quickstart.md`
- I want to extend framework functionality:
  - `docs/developer_guide/extension_handbook.md`
  - `docs/developer_guide/extension_recipes.md`
  - `docs/framework_extension_guide.md`
- I want to build a new agent flow quickly:
  - `docs/developer_guide/canonical_e2e_walkthrough.md`
  - `docs/developer_guide/examples_catalog.md`
  - `docs/developer_guide/api_reference.md`
- I need operations and release readiness:
  - `docs/developer_guide/operations_and_release.md`
  - `docs/developer_guide/release_reproducible_flow.md`
  - `docs/production_runbook.md`

## Architecture At A Glance

```text
Clients / Integrators
        |
        v
FastAPI + MCP Boundaries
        |
        v
Framework Layer (LangGraph Workflows)
        |
        v
Application Services (retrieval/indexing/authoring/HITL)
        |
        v
Persistence + Adapters (PostgreSQL, pgvector, external gateways)
```

Full architecture overview:

- `docs/architecture/System_Architecture_Overview.md`
- `docs/adr/README.md`

## Core Runtime Components

- API boundary: `backend/apps/api`
- MCP services: `backend/apps/mcp_*`
- Worker execution plane: `backend/apps/worker`
- Framework and contracts: `backend/packages/framework`, `backend/packages/schemas`
- Scripts and gates: `backend/scripts`

## Extension Map

- `Workflow extension`: new graph/state-machine path.
  - Start: `docs/developer_guide/extension_handbook.md` (Workflow extension playbook)
- `Tool extension`: add domain tool with retry/idempotency/audit policy.
  - Start: `docs/developer_guide/extension_handbook.md` (Tool extension playbook)
- `MCP extension`: add or extend MCP service/toolset with scopes/roles.
  - Start: `docs/developer_guide/extension_handbook.md` (MCP extension playbook)
- `Persistence extension`: add store/read-model and additive migration.
  - Start: `docs/developer_guide/persistence_reference.md`
- `Domain extension`: add new business capability through `domain_*` + application service.
  - Start: `docs/developer_guide/extension_recipes.md`

## Public Contract Surface

Stable/experimental/internal matrix and versioning/deprecation policy:

- `docs/developer_guide/public_contract_surface.md`
- `docs/developer_guide/versioning_policy.md`

## Contributing and Governance

- Contributing: `CONTRIBUTING.md`
- Code of Conduct: `CODE_OF_CONDUCT.md`
- Security policy: `SECURITY.md`
- Support policy: `SUPPORT.md`

## License

Apache License 2.0 (`LICENSE`).

License rationale:

- `docs/oss_license_rationale.md`
