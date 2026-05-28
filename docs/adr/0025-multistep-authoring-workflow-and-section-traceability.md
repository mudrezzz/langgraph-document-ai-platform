# ADR-0025: Multi-step authoring workflow and section-level traceability

- Status: Accepted
- Date: 2026-04-20

## Context

After `Increment 19` authoring was already able to generate a “live” draft via OpenRouter, but the process remained single-pass.

What was missing:

- explicit research step before writer;
- reviewer of the stage with a formalized status/recommendation;
- transparent read-model for execution steps;
- traceability at the section level of the final artifact.

## Solution

1. Extend `AuthoringApplicationService` to a multi-step pipeline:
   - `research -> writer -> reviewer -> assembly`.
2. Add `workflow_mode` to the API contract `POST /api/v1/tasks/authoring/start`:
- `single_pass` (backwards compatible);
- `multi_step` (new default mode).
3. Save execution steps in task details and artifact metadata:
   - `steps_summary`;
   - `current_step`, `review_status`, `final_recommendation`.
4. Expand the traceability contract of the artifact:
- `traceability.sections[]` with `section_id`, `title`, `review_status`, `source_refs`.
5. Maintain existing LLM policy:
- writer step can use LLM (`draft_strategy=llm|auto`);
- if the gateway fails, fallback to deterministic mode is allowed (if strict is disabled).

## Consequences

Pros:

- authoring has become more explainable and verifiable (steps and reviewer verdict are visible);
- the read-model API for manual smoke and audit tracing has been expanded;
- section-level traceability makes artifact more suitable for checking sources.

Cons:

- the pipeline remains synchronous (no queues and async retries);
- reviewer is still rule-based, without HITL/revision-loop;
- section mapping is still heuristic.
