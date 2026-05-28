# ADR-0009: Reference-case and mandatory e2e FastAPI tests

- Status: Accepted
- Date: 2026-04-17

## Context

As the framework grows, you need to have a stable and business-friendly indicator of progress: not only unit/integration tests, but also a constant realistic scenario that becomes more complex from iteration to iteration.

## Solution

1. Enter a constant reference-case:
- `saa_release_readiness_case` with test knowledge layers.
2. Link the retrieval workflow to the case dataset via `task_context` (`case_dataset_id` / `case_dataset_path`).
3. Add mandatory e2e FastAPI tests on real `uvicorn`:
   - `backend/tests/e2e/test_fastapi_retrieval_e2e.py`.
4. Add a demo-run script for a visual run of the case:
   - `backend/scripts/demo_saa_release_readiness_case.ps1`.

## Consequences

Pros:

- an end-to-end indicator of platform development appears, close to reality;
- progress is visible through a stable business scenario;
- e2e layer catches problems that are not visible in TestClient-only tests.

Cons:

- the test circuit becomes heavier and requires fixture data support;
- when contracts change, you need to synchronously update the reference-case.
