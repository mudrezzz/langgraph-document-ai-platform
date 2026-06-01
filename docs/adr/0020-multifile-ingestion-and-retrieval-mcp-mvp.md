# ADR-0020: Multi-File Ingestion and Retrieval MCP MVP

- Status: Accepted
- Date: 2026-04-20

## Context

After `Increment 14`, retrieval supported built-in datasets (`case_dataset_id`) and file-based JSON (`case_dataset_path`), but in actual manual runs the input usually comes as a collection of documents rather than a single pre-assembled JSON.

Also in architectural terms, the first working FastMCP runtime service was required for a gradual transition from the API-only boundary to the MCP boundary.

## Solution

1. Add a new data source mode `task_context.case_dataset_dir`:
- ingestion directory with files `.md/.txt/.json`;
- building summary/detail blocks at runtime without intermediate manual JSON assembly.
2. Fix the priority of retrieval dataset sources:
   - `case_dataset_path` -> `case_dataset_dir` -> `case_dataset_id`.
3. Add a new realistic demo-case:
   - `backend/examples/cases/release_go_no_go_multifile_case`.
4. Add Retrieval MCP MVP:
   - `apps/mcp_retrieval/main.py`;
   - `FastMcpRetrievalService`;
- minimal MCP tool `build_evidence_pack`.
5. Update smoke/demo contour:
- `smoke_retrieval_api.sh/.ps1` support `case_dataset_dir`.

## Consequences

Pros:

- manual smoke/demo is closer to real operation (several input artifacts);
- retrieval API gets a more flexible ingestion circuit without breaking current paths;
- the first working MCP runtime boundary for the retrieval domain appeared in the system.

Cons:

- ingestion currently only covers `.md/.txt/.json` (without PDF/DOCX/OCR);
- Retrieval MCP still contains a minimal set of tools and does not cover the full blueprint contract;
- for production MCP needs, auth/rate-limit/observability policies and a separate deployment profile will be required.
