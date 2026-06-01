# ADR-0023: Authoring API Flow and task->artifact traceability link

- Status: Accepted
- Date: 2026-04-20

## Context

After `Increment 17` the system already had Retrieval/Repository/Artifact Writer MCP services, but there was no single API flow, which:

- runs the authoring task on top of retrieval;
- forms the final artifact;
- preserves traceability between task, retrieval sources and artifact.

Without this API boundary remained retrieval-centric, and the authoring scenario required manual orchestration of several MCP tools.

## Solution

1. Add authoring API lifecycle:
   - `POST /api/v1/tasks/authoring/start`;
   - `GET /api/v1/tasks/{task_id}/artifact`.
2. Add `AuthoringApplicationService`:
   - orchestration `retrieval -> draft -> artifact`;
- recording task checkpoint + details in the general lifecycle circuit.
3. Enter a persistence link between the task and the artifact:
- table `app.task_artifacts` (migration `0007_task_artifacts.sql`);
- `PostgresTaskArtifactRegistry` adapter.
4. Add traceability contract to the API:
   - `retrieval_task_id`;
- `source_refs` (`doc_id/version/block_id`) for the resulting artifact.
5. Add smoke/demo for authoring API:
   - `smoke_authoring_api.sh/.ps1` (+ python runner);
   - `demo_release_authoring_traceability_case.sh/.ps1`.

## Consequences

Pros:

- a minimal end-to-end authoring flow has appeared on the API boundary;
- traceability between task/evidence/artifact has become persistent and readable via the API;
- smoke/runbook covers the new authoring script in the `prod` profile.

Cons:

- authoring draft is still rule-based (without a separate LLM section writer/reviewer cycle);
- `task_artifacts` in MVP assumes 1 artifact per task (PK by `task_id`);
- list/read-model for authoring artifacts while offset-based and without a separate dashboard layer.
