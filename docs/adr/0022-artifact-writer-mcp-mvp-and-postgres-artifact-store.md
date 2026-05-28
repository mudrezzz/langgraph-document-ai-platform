# ADR-0022: Artifact Writer MCP MVP and PostgreSQL Artifact Store

- Status: Accepted
- Date: 2026-04-20

## Context

After `Increment 16` the MCP circuit already included Retrieval and Repository services, but there was no separate runtime boundary for recording generated artifacts.

Gaps left:

- there was no separate persistence circuit for artifacts;
- there was no MCP contract for writing/reading/listing artifacts;
- the runbook did not cover manual smoke artifact writer scripts.

## Solution

1. Add a selected persistence artifact layer:
- `PostgresArtifactStore` with fallback mode;
- SQL migration `0006_artifact_store.sql` (`app.artifacts` + index by `artifact_type/updated_at`).
2. Enter the artifact application service:
   - `ArtifactApplicationService` (`write_artifact`, `get_artifact`, `list_artifacts`).
3. Add Artifact Writer MCP MVP:
   - app entrypoint `apps/mcp_artifact_writer/main.py`;
- service `FastMcpArtifactWriterService`;
   - MCP tools: `write_artifact`, `get_artifact`, `list_artifacts`.
4. Fix typed MCP contracts:
   - `schemas/mcp/artifact_writer.py`.
5. Add operational scripts and smoke:
- launch runtime `run_artifact_writer_mcp.sh/.ps1`;
- manual smoke `smoke_artifact_writer_mcp.py` + wrappers `smoke_artifact_writer_mcp.sh/.ps1`.

## Consequences

Pros:

- The MCP circuit has been expanded to three services: Retrieval + Repository + Artifact Writer;
- generated artifacts received dedicated PostgreSQL storage and an explicit read/write contract;
- manual runbook now covers smoke for the artifact writer outline.

Cons:

- `list_artifacts` in MVP uses `limit/offset` rather than cursor pagination;
- Artifact Writer MCP does not yet have auth/rate-limit/observability policies;
- MVP does not include a full authoring workflow/assembly, but only storage-boundary and MCP tools.
