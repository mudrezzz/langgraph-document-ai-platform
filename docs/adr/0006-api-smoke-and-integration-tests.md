# ADR-0006: Smoke script and integration tests of API endpoints

- Status: Accepted
- Date: 2026-04-17

## Context

With the introduction of the API boundary, there is a need for a fast and reproducible way to test the runtime path of endpoints in the local environment, as well as regression coverage of each endpoint at the test level.

## Solution

1. Add smoke script `backend/scripts/smoke_retrieval_api.ps1`.
2. In the script, launch uvicorn, wait for `health`, then run the path:
   - start;
   - status;
   - evidence;
   - resume.
3. Add `backend/tests/integration/test_api_endpoints.py` with tests for each endpoint (successful and 404 branches).

## Consequences

Pros:

- manual API checking has been accelerated without manually copying commands;
- each endpoint has integration coverage;
- it is easier to control task lifecycle regressions.

Cons:

- smoke script is currently designed for local single-process launch;
- does not cover distributed configuration and external services of the production circuit.
