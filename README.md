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

## Install as a Library

The framework core (`framework`, `schemas`, `infra.openrouter`) is available as
a pip-installable package directly from this repository — no PyPI account needed.

**Install latest from `main`:**

```bash
pip install "langgraph-dai @ git+https://github.com/mudrezzz/langgraph-document-ai-platform.git@main#subdirectory=backend/packages"
```

**Install a pinned release (reproducible builds):**

```bash
pip install "langgraph-dai @ git+https://github.com/mudrezzz/langgraph-document-ai-platform.git@v0.1.0#subdirectory=backend/packages"
```

**In `requirements.txt`:**

```
langgraph-dai @ git+https://github.com/mudrezzz/langgraph-document-ai-platform.git@v0.1.0#subdirectory=backend/packages
```

**Then import as usual:**

```python
from framework.workflows.base import BaseWorkflow, WorkflowNodeSpec
from framework.models.interfaces import IChatModelGateway
from schemas.rag.contracts import EvidencePack
from infra.openrouter.chat_gateway import OpenRouterChatModelGateway
```

What is included: `framework`, `schemas`, `infra.openrouter`.
What is excluded: PostgreSQL, Celery, pgvector, FastAPI — these are part of the
full backend install and not needed for in-process agent development.

---

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

## Copy-Paste Starters

Retrieval-first starter:

```bash
bash backend/scripts/postgres_up.sh
bash backend/scripts/postgres_migrate.sh
.venv/bin/python agent_examples/run_example.py --pattern retrieval_first
```

Device-search starter (in-process workflow; requires `OPENROUTER_API_KEY`, no backend API required):

```bash
export OPENROUTER_API_KEY="sk-or-..."
.venv/bin/python agent_examples/run_example.py --pattern device_search
```

Authoring-first starter:

```bash
bash backend/scripts/postgres_up.sh
bash backend/scripts/postgres_migrate.sh
.venv/bin/python agent_examples/run_example.py --pattern authoring_first
```

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

## Example Gallery And Patterns

- Product-style Python agent examples (single folder, no framework internals required):
  - `agent_examples/README.md`
  - `.venv/bin/python agent_examples/run_example.py --pattern retrieval_first`
  - `.venv/bin/python agent_examples/run_example.py --pattern authoring_first`
  - `.venv/bin/python agent_examples/run_example.py --pattern hitl_gate --hitl-decisions needs_changes,approve`
  - current status: `retrieval_first` is in-process framework pattern, `authoring_first/hitl_gate` are transition API-driven patterns.
- Design patterns library:
  - `docs/developer_guide/design_patterns/README.md`
  - Retrieval-First, Authoring-First, HITL Gate templates with runnable paths.

## 30-Second Architecture Story

1. You send documents and tasks through API/MCP boundaries with typed contracts.
2. LangGraph workflows orchestrate retrieval/indexing/authoring and optional HITL loop.
3. PostgreSQL + pgvector persist state, evidence, artifacts, and observability traces.

What this gives your team:

- Faster delivery: reusable extension surface for workflows, tools, and MCP services.
- Lower risk: auditable lifecycle with task events, HITL actions, and release gates.
- Cleaner ownership: contract-first boundaries between product, platform, and infra teams.

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
