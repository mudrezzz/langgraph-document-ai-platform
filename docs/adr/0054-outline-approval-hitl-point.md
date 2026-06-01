# ADR-0054: Outline approval HITL point

- Status: Accepted
- Date: 2026-04-24

## Context

By this stage, `Increment 28` already had the `SectionContract` typed, section-level traceability, template-aware assembly and artifact export, but HITL was still only enabled after section authoring / draft generation. A separate `outline approval` point was initially included in the increment backlog so that the reviewer could stop the pipeline earlier, before generating sectional artifacts.

## Solution

1. With `hitl_required=true` and `workflow_mode=multi_step`, transfer the authoring task to `waiting_human` after constructing outline/section contracts, but before section authoring.
2. Store `hitl_phase=outline_review` in state and `outline_snapshot` in `task_context`.
3. Expand the HITL read-model response with fields:
   - `phase`;
   - `outline` (`template_id`, sections, objectives, required keywords, source refs).
4. When `approve` continue the usual pipeline: section authoring -> final review -> assembly/export.
5. When `needs_changes` is in the outline phase, do not run rewrite, but return the task back to `waiting_human` with an updated pending reason.
6. Do not change public endpoints.

## Consequences

Pros:

- reviewer can stop authoring earlier and see the document plan before generating sections;
- future section workflows and reviewer UI are easier to build on top of an already typed outline snapshot;
- expensive steps with section generation are not launched before outline approval.

Cons:

- `needs_changes` on the outline phase does not yet recalculate the outline automatically and requires an external rerun/input change;
- the current HITL flow has become two-phase (`outline_review` -> `final_review`) only at the state/read-model level, without a separate UI.
