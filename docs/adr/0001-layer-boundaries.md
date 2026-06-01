# ADR-0001: System Layer Boundaries

- Status: Accepted
- Date: 2026-04-17

## Context

It is required to separate the framework, domain and infrastructure so that application logic does not depend on specific libraries and services.

## Solution

Adopt layered model:

1. `packages/schemas` - a single point of truth for typed contracts.
2. `packages/framework` - abstractions and basic implementations of runtime patterns.
3. `packages/domain_*` - applied business logic on top of the framework interfaces.
4. `infra/*` and service adapters - concrete implementation of external integrations.

## Consequences

Pros:

- predictable dependency structure;
- simplification of contract testing;
- convenient replacement of specific adapters.

Cons:

- higher disciplinary burden on the team;
- more interface code at the start.
