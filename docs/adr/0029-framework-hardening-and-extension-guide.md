# ADR-0029: Framework hardening and extension guide

- Status: Accepted
- Date: 2026-04-23

## Context

After `Increment 23` the framework layer already contains the main contracts and runtime primitives:

- agents/tools/workflows/rag/stores/db/models/hitl/mcp;
- LangGraph-backed `BaseWorkflow`;
- Postgres persistence adapters;
- FastAPI/MCP service boundaries;
- async authoring and iterative HITL.

The next increments will expand the ingestion, retrieval and authoring domains. Without an explicit extension guide and contract tests, new domain implementations may begin to bypass framework boundaries and enforce temporary shortcuts.

## Solution

1. Record a separate document `docs/framework_extension_guide.md`.
2. Add root backlog `BACKLOG.md` as a work plan for completing the backend/framework part.
3. Strengthen unit coverage for basic framework contracts:
   - agents;
   - tools;
   - MCP service metadata;
   - repository factory/unit of work;
   - base stores.
4. Consider release go/no-go scripts mandatory acceptance demo harness for the next increments.

## Consequences

Pros:

- new workflows/tools/MCP services receive a single addition path;
- the framework layer becomes a verifiable contract surface, and not just a set of skeleton classes;
- demo scripts are attached as a regression harness for manual testing.

Cons:

- the volume of documentation that needs to be updated with each increment increases;
- the tests part fixes the current minimal behavior skeleton and will require a conscious update during the development of the framework.
