# Examples Catalog

Update date: 2026-06-02
Status: Active (P2 cookbook)

Directory of reusable scripts for integrators.

## 1. Retrieval-first

Use case: quickly collect an evidence pack on an issue without a full authoring flow.

Primary assets:

- Case:
  - `backend/examples/cases/saa_release_readiness_case/input/knowledge_layers.json`
- Demo:
  - `backend/scripts/demo_saa_release_readiness_case.sh`
  - `backend/scripts/demo_saa_release_readiness_case.ps1`
- Smoke:
  - `backend/scripts/smoke_retrieval_api.sh`
  - `backend/scripts/smoke_retrieval_async_api.sh`

Expected proof:

- task lifecycle `start -> completed`;
- evidence pack with `selected_blocks` and `source_refs`;
- task events/summary are available via API.

## 2. Authoring-first

Use case: generate the final artifact with traceability and go through the HITL loop.

Primary assets:

- Case:
  - `backend/examples/cases/release_go_no_go_case/input/release_packet.md`
- Demo:
  - `backend/scripts/demo_release_authoring_traceability_case.sh`
  - `backend/scripts/demo_release_authoring_async_hitl_case.sh`
- Smoke:
  - `backend/scripts/smoke_authoring_api.sh`
  - `backend/scripts/smoke_authoring_async_api.sh`

Expected proof:

- artifact is available via `GET /api/v1/tasks/{task_id}/artifact`;
- `traceability.retrieval_task_id` and `source_refs` are filled;
- for async/HITL script the `waiting_human -> completed` transition is visible.

## 3. MCP-first

Use case: agent integration via MCP tools instead of direct HTTP API.

Primary assets:

- Retrieval MCP:
  - run: `backend/scripts/run_retrieval_mcp.sh`
  - smoke: `backend/scripts/smoke_retrieval_mcp.sh`
- Repository MCP:
  - run: `backend/scripts/run_repository_mcp.sh`
  - smoke: `backend/scripts/smoke_repository_mcp.sh`
- Artifact Writer MCP:
  - run: `backend/scripts/run_artifact_writer_mcp.sh`
  - smoke: `backend/scripts/smoke_artifact_writer_mcp.sh`
- Template Library MCP:
  - run: `backend/scripts/run_template_library_mcp.sh`
  - smoke: `backend/scripts/smoke_template_library_mcp.sh`
- Review/Approval MCP:
  - run: `backend/scripts/run_review_approval_mcp.sh`
  - smoke: `backend/scripts/smoke_review_approval_mcp.sh`
- Configuration Library MCP:
  - run: `backend/scripts/run_configuration_library_mcp.sh`
  - smoke: `backend/scripts/smoke_configuration_library_mcp.sh`

Expected proof:

- tool contracts work with typed payloads;
- RBAC-sensitive tools correctly handle `actor`/`roles` when `APP_AUTH_ENABLED=true`.

## 4. Canonical ingestion + retrieval

Use case: multi-format corpus (`.md/.txt/.json/.docx/.pdf/.xlsx/.pptx`) and retrieval by canonical store.

Primary assets:

- Case:
  - `backend/examples/cases/release_go_no_go_multifile_case/input/*`
- Demo:
  - `backend/scripts/demo_release_go_no_go_multifile_case.sh`
- Smoke:
  - `backend/scripts/smoke_knowledge_indexing_api.sh --build-binary-demo-docs`
  - `backend/scripts/smoke_canonical_retrieval.sh --build-binary-demo-docs`

Expected proof:

- `quality_gate_status` present;
- `retrieval_backend=pgvector`;
- report contains `Canonical Quality Summary` and `Canonical Source Mapping`.

## 5. Scenario selection guide

- All you need is a search for evidence -> `Retrieval-first`.
- We need the final document -> `Authoring-first`.
- Need tool integration for agent -> `MCP-first`.
- We need a multi-format ingestion pipeline -> `Canonical ingestion + retrieval`.
- We need queue-like processing for many retrieval prompts -> `Async batch` (`agent_examples/patterns/async_batch`).
- We need one core agent behind MCP tools -> `MCP tool facade` (`agent_examples/patterns/mcp_tool_facade`).

## 6. Related docs

- `backend/examples/README.md`
- `agent_examples/README.md`
- `docs/developer_guide/design_patterns/README.md`
- `docs/developer_guide/canonical_e2e_walkthrough.md`
- `docs/developer_guide/mcp_reference.md`
- `docs/developer_guide/release_reproducible_flow.md`
