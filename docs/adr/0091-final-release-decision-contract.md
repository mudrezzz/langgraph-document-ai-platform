# ADR-0091: Final release decision contract

- Status: Accepted
- Date: 2026-04-29

## Context

After ADR-0090, unified release-gate smoke with machine-readable checks appeared, but the final release decision was still collected manually from several steps:

- launch smoke gate;
- launch the full pytest gate;
- manual interpretation of results for handoff.

We need a single orchestrator who forms the official release verdict.

## Solution

1. Added final orchestrator:
   - `backend/scripts/release_decision_gate.py` + wrappers `.sh/.ps1`.
2. Orchestrator does:
   - `smoke_release_gate` (profile-aware);
- full pytest gate (default);
- collection of unified release decision payload.
3. Unified payload is saved in:
   - `backend/.release_gate/release_decision_<timestamp>.json`;
   - `backend/.release_gate/release_decision_<timestamp>.md`.
4. Contract payload:
   - `status: pass|fail`;
   - `decision_reason`;
- `failed_checks[]` (from smoke gate);
   - `smoke_release_gate` summary;
   - `test_gate_summary`;
   - `profile`, `commit_sha`, `branch`, `timestamp_utc`.

## Consequences

Pros:

- a single source-of-truth release verdict appears for stage/prod handoff;
- the risk of human error in the final gate is reduced;
- JSON/Markdown artifacts simplify the audit and retrospective of release decisions.

Cons:

- orchestrator remains integration-dependent on the runtime environment;
- with a long full gate, you may need profile-specific split (fast/full) in the future.
