# ADR-0015: Smoke Keep-Server Mode for post-smoke API validation

- Status: Accepted
- Date: 2026-04-19

## Context

The manual test operational scenario required performing additional `curl` requests to the API immediately after smoke (for example, checking `GET /api/v1/tasks/events` against `task_id`).

Previously, `smoke_retrieval_api.sh` always stopped `uvicorn` in `cleanup`, so manual check after the script failed with `connection refused`.

## Solution

1. Add the `--keep-server` flag to `smoke_retrieval_api.sh`.
2. In `--keep-server` mode:
- leave the API process raised after smoke;
- write PID to a file (by default `backend/.smoke_uvicorn_<port>.pid`);
- output the stop command to stderr.
3. Add `--server-pid-file <path>` to explicitly control the PID of the file.
4. Add a pre-check for a busy port before starting smoke to eliminate false success on an already running API.

## Consequences

Pros:

- you can immediately perform manual API checks against `task_id` immediately after smoke;
- the procedure for stopping the server after a manual check has been standardized;
- the risk of a false smoke-pass on someone else's process has been reduced.

Cons:

- an additional operating mode has appeared, which must be explicitly stopped after checking.
