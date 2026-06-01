# ADR-0044: Retrieval MCP indexed canonical tools

- Status: Accepted
- Date: 2026-04-24

## Context

Retrieval MCP started out as an MVP with one tool `build_evidence_pack`. After ADR-0041..0043, retrieval fabric is already able to work with indexed canonical summary/detail layers, real TEI gateways and quality gates, but the MCP boundary did not give agents direct access to production corpus search and source mapping.

You cannot introduce a separate MCP-specific retrieval architecture: canonical indexing, pgvector search and source lookup already have application/infra boundaries.

## Solution

1. Extend `FastMcpRetrievalService` tools:
   - `search_summaries`;
   - `search_blocks`;
   - `lookup_source`.
2. Leave `build_evidence_pack` without changing the external contract.
3. `search_summaries` uses `CanonicalSummaryVectorRetriever` with injected `embedding_gateway` and `vector_store`.
4. `search_blocks` uses `CanonicalVectorRetriever` with the same dependencies.
5. `lookup_source` reads canonical document/block metadata via `CanonicalDocumentApplicationService`.
6. Add typed MCP schemas to `schemas.mcp.retrieval`.
7. Runtime assembly in `apps/mcp_retrieval/main.py` takes dependencies from the existing `ApiContainer`.

## Consequences

Pros:

- MCP consumers can search for indexed canonical summaries/details without running the full retrieval task;
- source mapping is available through the same canonical read boundary as ingestion/retrieval reports;
- Retrieval MCP reuses production adapters and does not create a parallel search stack;
- the old `build_evidence_pack` MCP contract remains compatible.

Cons:

- indexed search tools require configured `embedding_gateway` and `vector_store`;
- operational smoke for direct MCP calls still needs to be allocated as a separate script slice;
- metadata schema vector records still remain free and should be stabilized along with retrieval adapter contracts.
