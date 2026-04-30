# Examples Catalog

Дата обновления: 2026-04-30  
Статус: Active (P2 cookbook)

Каталог reusable сценариев для integrators.

## 1. Retrieval-first

Use case: быстро собрать evidence pack по вопросу без полного authoring flow.

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
- evidence pack с `selected_blocks` и `source_refs`;
- task events/summary доступны через API.

## 2. Authoring-first

Use case: сгенерировать итоговый артефакт с traceability и пройти HITL loop.

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

- artifact доступен через `GET /api/v1/tasks/{task_id}/artifact`;
- `traceability.retrieval_task_id` и `source_refs` заполнены;
- для async/HITL сценария виден переход `waiting_human -> completed`.

## 3. MCP-first

Use case: интеграция агента через MCP tools вместо прямого HTTP API.

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

- tool contracts работают с typed payloads;
- RBAC-sensitive tools корректно обрабатывают `actor`/`roles` при `APP_AUTH_ENABLED=true`.

## 4. Canonical ingestion + retrieval

Use case: multi-format corpus (`.md/.txt/.json/.docx/.pdf/.xlsx/.pptx`) и retrieval по canonical store.

Primary assets:

- Case:
  - `backend/examples/cases/release_go_no_go_multifile_case/input/*`
- Demo:
  - `backend/scripts/demo_release_go_no_go_multifile_case.sh`
- Smoke:
  - `backend/scripts/smoke_knowledge_indexing_api.sh --build-binary-demo-docs`
  - `backend/scripts/smoke_canonical_retrieval.sh --build-binary-demo-docs`

Expected proof:

- `quality_gate_status` присутствует;
- `retrieval_backend=pgvector`;
- report содержит `Canonical Quality Summary` и `Canonical Source Mapping`.

## 5. Scenario selection guide

- Нужен только поиск доказательств -> `Retrieval-first`.
- Нужен финальный документ -> `Authoring-first`.
- Нужна tool-интеграция для агента -> `MCP-first`.
- Нужен multi-format ingestion pipeline -> `Canonical ingestion + retrieval`.

## 6. Related docs

- `docs/developer_guide/canonical_e2e_walkthrough.md`
- `docs/developer_guide/mcp_reference.md`
- `docs/developer_guide/release_reproducible_flow.md`
