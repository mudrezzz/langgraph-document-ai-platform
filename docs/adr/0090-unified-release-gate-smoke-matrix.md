# ADR-0090: Unified release-gate smoke matrix

- Status: Accepted
- Date: 2026-04-29

## Context

After ADR-0088/0089, the platform already has execution, quality, token and SLA metrics, but before that they were checked separately through separate smoke scripts and manual curl.

Increment 32 requires a single gate-proof contract:

- machine-readable pass/fail verdict;
- single point of verification retrieval/authoring/HITL/observability;
- configurable thresholds without changing the code.

## Solution

1. Added unified script `backend/scripts/smoke_release_gate.py` (+ `.sh/.ps1` wrappers).
2. Smoke picks up the API and executes the sequence:
   - optional knowledge indexing;
   - retrieval task + `events/summary`;
- authoring task with HITL loop;
- `tasks/observability/summary` and `hitl/observability/summary`.
3. The Script builds the checks matrix and prints JSON:
   - `gate_status=pass|fail`;
- `checks[]` with the structure `code/name/passed/expected/actual/message`;
- `failed_checks[]` for quick triage;
- `artifacts` with input payloads for diagnostics.
4. Threshold checks are parameterized via env/CLI and profile presets:
   - `--gate-profile dev|stage|prod`;
   - `APP_RELEASE_GATE_MIN_EVENTS_TOTAL`;
   - `APP_RELEASE_GATE_MIN_OBSERVABILITY_TOTAL_TASKS`;
   - `APP_RELEASE_GATE_MAX_DURATION_SLA_BREACHES`;
   - `APP_RELEASE_GATE_MAX_QUEUE_WAIT_SLA_BREACHES`;
   - `APP_RELEASE_GATE_REQUIRE_LLM_TOKENS`.

## Consequences

Pros:

- release gate becomes repeatable and CI-friendly;
- manual stage/prod rehearsal receives a deterministic verdict;
- diagnosing problems is simplified due to a single JSON proof payload.

Cons:

- smoke is still integration and depends on the runtime environment (DB/env/gateways);
- with further growth of the matrix, it may be necessary to split it into several gate profiles (fast/full/llm).
