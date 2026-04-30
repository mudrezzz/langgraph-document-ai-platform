# MCP Reference (FastMCP Services)

Дата обновления: 2026-04-30  
Статус: Active (P0 reference)

Источник истины: `backend/apps/mcp_*/main.py`, `backend/packages/infra/fastmcp/*_service.py`, `backend/packages/schemas/mcp/*.py`.

## 1. Общая MCP policy

Все сервисы наследуют `BaseFastMcpService` и используют единые правила:

- transport: `fastmcp`
- policy version: `mcp-policy-v1`
- operation scopes: `read | write | action`
- input/output validation: Pydantic (`model_validate` / typed response models)
- error mapping: доменные ошибки возвращаются как `ValueError` с понятным текстом

Auth policy:

- включается через `APP_AUTH_ENABLED=true`
- sensitive tools требуют `actor` + `roles` в payload
- роли проверяются per-tool через `_authorize_tool(...)`

## 2. Service matrix

| Service | Tool | Scope | Required role |
|---|---|---|---|
| `retrieval-mcp` | `build_evidence_pack` | `action` | - |
| `retrieval-mcp` | `search_summaries` | `read` | - |
| `retrieval-mcp` | `search_blocks` | `read` | - |
| `retrieval-mcp` | `lookup_source` | `read` | - |
| `repository-mcp` | `upsert_document` | `write` | `repository_writer` |
| `repository-mcp` | `get_document` | `read` | - |
| `repository-mcp` | `list_documents` | `read` | - |
| `artifact-writer-mcp` | `write_artifact` | `write` | `artifact_writer` |
| `artifact-writer-mcp` | `get_artifact` | `read` | - |
| `artifact-writer-mcp` | `list_artifacts` | `read` | - |
| `template-library-mcp` | `upsert_template` | `write` | `template_admin` |
| `template-library-mcp` | `publish_template` | `write` | `template_admin` |
| `template-library-mcp` | `set_template_status` | `write` | `template_admin` |
| `template-library-mcp` | `get_template` | `read` | - |
| `template-library-mcp` | `list_templates` | `read` | - |
| `review-approval-mcp` | `get_hitl_status` | `read` | - |
| `review-approval-mcp` | `list_hitl_actions` | `read` | - |
| `review-approval-mcp` | `submit_hitl_review` | `write` | `reviewer` |
| `review-approval-mcp` | `get_hitl_observability_summary` | `read` | - |
| `configuration-library-mcp` | `upsert_config` | `write` | `config_admin` |
| `configuration-library-mcp` | `get_config` | `read` | - |
| `configuration-library-mcp` | `list_configs` | `read` | - |
| `configuration-library-mcp` | `find_similar_configs` | `read` | - |
| `configuration-library-mcp` | `compare_configs` | `read` | - |

## 3. Contracts by schema module

- Retrieval MCP: `schemas/mcp/retrieval.py`
- Repository MCP: `schemas/mcp/repository.py`
- Artifact Writer MCP: `schemas/mcp/artifact_writer.py`
- Template Library MCP: `schemas/mcp/template_library.py`
- Review/Approval MCP: `schemas/mcp/review_approval.py`
- Configuration Library MCP: `schemas/mcp/configuration_library.py`

## 4. Error semantics

- Validation errors:
  - некорректный payload -> Pydantic validation error.
- Auth errors (when enabled):
  - нет actor/roles при обязательной роли -> authentication/authorization error mapped в operation error.
- Domain not found/state errors:
  - например `DocumentNotFoundError`, `TemplateNotFoundError`, `InvalidTaskStateError` -> operation error с текстом причины.

Практическое правило: MCP client должен трактовать tool error как non-2xx operation result и читать текст ошибки.

## 5. Runtime entrypoints и smoke

Run scripts:

- `backend/scripts/run_retrieval_mcp.sh`
- `backend/scripts/run_repository_mcp.sh`
- `backend/scripts/run_artifact_writer_mcp.sh`
- `backend/scripts/run_template_library_mcp.sh`
- `backend/scripts/run_review_approval_mcp.sh`
- `backend/scripts/run_configuration_library_mcp.sh`

Smoke scripts:

- `backend/scripts/smoke_retrieval_mcp.sh`
- `backend/scripts/smoke_repository_mcp.sh`
- `backend/scripts/smoke_artifact_writer_mcp.sh`
- `backend/scripts/smoke_template_library_mcp.sh`
- `backend/scripts/smoke_review_approval_mcp.sh`
- `backend/scripts/smoke_configuration_library_mcp.sh`

## 6. Связанные документы

- `docs/developer_guide/public_contract_surface.md`
- `docs/developer_guide/api_reference.md`
- `docs/developer_guide/operations_and_release.md`
