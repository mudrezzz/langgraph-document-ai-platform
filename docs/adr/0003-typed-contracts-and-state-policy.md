# ADR-0003: Typed contracts and state policy

- Status: Accepted
- Date: 2026-04-17

## Context

The system uses a large number of cross-layer contracts: API, workflow state, RAG, MCP, approvals.

## Solution

- Pydantic v2 is used as the base format for describing payload/state contracts.
- Framework interfaces are specified via `Protocol`/`ABC` with typing.
- Workflow state stores only orchestration-significant fields.
- Large payloads are placed in stores and transmitted through links/identifiers.

## Consequences

Pros:

- stable contracts between teams;
- early validation of data errors;
- predictable migration and versioning of schemas.

Cons:

- it is required to maintain compatibility of schemes during evolution.
