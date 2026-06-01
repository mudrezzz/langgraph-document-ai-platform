# ADR-0069: Configuration Library MCP Skeleton

- Status: Accepted
- Date: 2026-04-27

## Context

By the beginning of Increment 30, the platform already had MCP boundaries for retrieval, repository, artifact writer, template library and reviewer/HITL. But the target architecture from the specification also needs a separate circuit for reusable configuration artifacts: typical retrieval policies, governance bundles, quality profiles and similar operational configs.

Without such a boundary, an external agent or operator must either store configurations outside the platform or directly know the internal tables and payload shape. This contradicts the goal of Increment 30: to make a production-like service boundary, rather than a set of internal adapter entrypoints.

## Solution

1. Add a separate persisted domain `configuration_library` with versioned JSON configuration records.
2. Implement the application boundary `ConfigurationLibraryApplicationService` on top of `PostgresConfigurationStore`.
3. Add FastMCP service `configuration-library-mcp` with typed schemas `schemas.mcp.configuration_library`.
4. In the first production-compatible slice, support tools:
   - `upsert_config`;
   - `get_config`;
   - `list_configs`;
   - `find_similar_configs`;
   - `compare_configs`.
5. For `find_similar_configs` use deterministic similarity heuristic on top of existing persisted records, rather than introducing a separate vector/runtime stack. This is sufficient for the skeleton layer and does not create a new parallel architecture.
6. `compare_configs` should be built as a deterministic payload diff using flattened JSON paths, so that the caller can see the changed settings without access to raw storage internals.

## Consequences

Pros:

- MCP surface closes another mandatory service from the technical specifications and blueprint;
- reusable policy/config bundles can now be stored, versioned, read, compared and searched for analogues through a single typed boundary;
- skeleton does not entail a new retrieval/vector architecture and uses the same PostgreSQL/fallback patterns as other persisted services.

Cons:

- similarity search is still heuristic and deterministic, without semantic/vector search by configuration intent;
- lifecycle/governance statuses for config bundles have not yet been introduced and may be needed in the next separate slice;
- pagination `find_similar_configs` currently works on top of a limited candidate pool, which is acceptable for skeleton, but not for very large libraries without further indexing.
