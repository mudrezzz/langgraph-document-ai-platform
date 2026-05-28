# ADR-0005: API boundary and task lifecycle via application services

- Status: Accepted
- Date: 2026-04-17

## Context

After the first working retrieval workflow appeared, a service boundary was required through which the UI and external clients could launch tasks, receive status, evidence, and execute resumes.

## Solution

1. Add `apps/api` to FastAPI as an HTTP boundary.
2. Place the orchestration composition in the `application` layer:
- `TaskApplicationService` for task registry/checkpoints;
- `RetrievalApplicationService` for the retrieval script.
3. Use typed request/response contracts (`schemas/api/contracts.py`).
4. At Increment 3, use a synchronous retrieval execution model in one process.

## Consequences

Pros:

- the API boundary is separated from the domain logic;
- the operability of the end-to-end path `start -> status -> evidence -> resume` has been confirmed;
- fixed template for the following application services.

Cons:

- there is no asynchronous task runner yet;
- no integration with real LangGraph runtime executor;
- persistence while in-memory via adapter skeleton.
