# ADR-0019: File-Based Demo Pipeline for Release Go/No-Go

- Status: Accepted
- Date: 2026-04-20

## Context

The current reference demo (`saa_release_readiness`) relied on a pre-prepared JSON dataset and poorly showed a scenario close to production operation: input document -> preparing the retrieval layer -> launching a task -> artifact for making a decision.

Manual smoke on the server required a more realistic but compact example with a meaningful result that could be interpreted without reading the internal JSON.

## Solution

1. Add a new demo case `release_go_no_go_case` with input in markdown format:
   - `backend/examples/cases/release_go_no_go_case/input/release_packet.md`.
2. Enter the markdown converter -> retrieval dataset:
- `build_release_packet_dataset(...)` in `domain_rag.retrieval.release_packet_dataset`;
- CLI script `backend/scripts/build_release_packet_dataset.py`.
3. Use the existing contract `task_context.case_dataset_path` to run retrieval on the dataset file.
4. Add post-processing demo step:
- script `backend/scripts/build_release_readiness_report.py`;
- output artifact `release_readiness_report.md` with GO/NO-GO, blockers, approvals, evidence sources and task events summary.
5. Add end-to-end demo orchestrator:
   - Linux: `backend/scripts/demo_release_go_no_go_case.sh`;
   - Windows: `backend/scripts/demo_release_go_no_go_case.ps1`.
6. Strengthen the stability of smoke/demo launch:
- priority of the local `./.venv` interpreter;
- explicit check for the presence of `uvicorn` before the API starts.

## Consequences

Pros:

- demo has become closer to a real user flow with file input;
- the result of the run is now interpreted through a human-readable report, and not just through JSON;
- manual running on Ubuntu/Windows has become more stable due to the predictable choice of Python environment.

Cons:

- the markdown converter is currently tailored to the release packet structure (not a universal parser for any documents);
- the final report uses text-based heuristics (blockers/pending approvals), without LLM evaluation and without a separate authoring workflow.
