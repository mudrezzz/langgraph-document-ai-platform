# ADR-0012: Migration to Linux server and Bash operations profile

- Status: Accepted
- Date: 2026-04-19

## Context

Local development on Windows turned out to be heavy on the Docker workload. For further iterations, the project is transferred to a Linux server (Ubuntu 24), where it is necessary to have a standard operating circuit without dependence on PowerShell.

## Solution

1. Commit Linux scripts to `backend/scripts`:
   - `apply_migrations.sh`;
   - `postgres_up.sh`, `postgres_migrate.sh`, `postgres_down.sh`;
   - `smoke_retrieval_api.sh`;
   - `demo_saa_release_readiness_case.sh`.
2. Add separate documentation for scripts:
   - `backend/scripts/README.md`.
3. Fix the handoff document to start a new chat on the server:
   - `docs/handoff/2026-04-19_ubuntu24_server_handoff.md`.
4. Post further increments to the GitHub repository:
   - `https://github.com/mudrezzz/langgraph-document-ai-platform`.

## Consequences

Pros:

- the operating circuit is no longer tied to Windows/Powershell;
- launching PostgreSQL, migrations and smoke becomes the same for the server environment;
- the transition to the real server deployment cycle is accelerated.

Cons:

- two sets of scripts (`.ps1` and `.sh`) need to be maintained during the transition period;
- some scripts should now be regularly checked on both Linux and Windows.
