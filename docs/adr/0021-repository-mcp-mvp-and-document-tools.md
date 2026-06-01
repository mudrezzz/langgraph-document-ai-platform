# ADR-0021: Repository MCP MVP and basic document tools

- Status: Accepted
- Date: 2026-04-20

## Context

After `Increment 15` the system already had Retrieval MCP MVP, but there was no separate MCP circuit for working with repository documents. This created a GAP to the target architecture:

- MCP boundary covered only the retrieval scenario;
- there was no standard MCP contract for `upsert/get/list` document operations;
- manual smoke MCP circuits did not include the document repository tools check.

## Solution

1. Add application-document service:
   - `DocumentApplicationService` (`upsert_document`, `get_document`, `list_documents`);
- `DocumentListPage` page model for list operations.
2. Extend `PostgresDocumentRepository`:
- support for the list operation `list_documents(limit, offset)` in PostgreSQL and fallback mode;
- fallback storage stores `created_at/updated_at` for stable list order.
3. Enter Repository MCP MVP:
   - app entrypoint `apps/mcp_repository/main.py`;
- service `FastMcpRepositoryService`;
   - MCP tools: `upsert_document`, `get_document`, `list_documents`.
4. Fix typed MCP contracts:
- `schemas/mcp/repository.py` (input/output models for 3 tools).
5. Add operational scripts and smoke:
- launch MCP runtime: `run_repository_mcp.sh/.ps1`;
- manual smoke: `smoke_repository_mcp.py` + wrappers `smoke_repository_mcp.sh/.ps1`.

## Consequences

Pros:

- The MCP circuit has been expanded with a second working service (`Repository MCP`) on top of the existing Retrieval MCP;
- a typed document tools contract has appeared for the integration of external MCP clients;
- manual runbook and smoke cover basic document repository operations.

Cons:

- `list_documents` in MVP uses `limit/offset`, not cursor pagination;
- Repository MCP does not yet have auth/rate-limit/observability policies;
- MCP scripts are currently limited to basic CRUD/read-model operations (without artifact writer and orchestration between MCP services).
