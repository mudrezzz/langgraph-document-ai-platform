# ADR-0004: Adapter wiring and first vertical slice Retrieval

- Status: Accepted
- Date: 2026-04-17

## Context

After the basic framework skeleton, it was necessary to confirm that the architecture really allows you to assemble a working workflow through interfaces, without direct dependence of domain logic on concrete integrations.

## Solution

1. Enter a layer `infra/*` with concrete adapter skeleton.
2. Collect workflow through explicit dependency injection in the bootstrap module.
3. Implement the first working vertical slice: `RetrievalPackWorkflow`.
4. In workflow, save intermediate retrieval artifacts (`summary`, `detail`, `rerank`) via `RetrievalTrace`.

## Consequences

Pros:

- the viability of the contract architecture was tested;
- an application workflow assembly template has been generated;
- it’s easier to expand production adapters without changing the domain API.

Cons:

- current concrete adapters are not yet connected to the real infrastructure;
- the next increment is required for API boundary and runtime integration.
