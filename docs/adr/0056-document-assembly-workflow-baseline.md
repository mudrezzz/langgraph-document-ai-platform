# ADR-0056: Document assembly workflow baseline

- Status: Accepted
- Date: 2026-04-25

## Context

After ADR-0055, section authoring was already done through a typed workflow boundary, but the final document assembly and export were still direct calls to `DocumentAssembler` and `ArtifactExporter` from `AuthoringApplicationService`. This left the last part of the authoring pipeline outside the general workflow runtime path, although this is where the final content/format payload is generated, which is then saved as an artifact.

## Solution

1. Add `domain_authoring.DocumentAssemblyWorkflow` as a baseline workflow on top of the existing `DocumentAssembler` and `ArtifactExporter`.
2. Use typed `AssemblyWorkflowState` and multi-node path:
   - `assemble_document`;
   - `export_artifact`;
   - `finalize_document`.
3. Transfer `AuthoringApplicationService` to a final assembly/export call through a new workflow boundary, preserving the external authoring API and artifact payload contracts.
4. Leave the workflow deterministic and synchronous at this step: without a separate persistence/read-model layer and without a separate public endpoint.
5. Reuse existing domain services/adapters without introducing a parallel assembly/export architecture.

## Consequences

Pros:

- the entire deterministic authoring path now passes through workflow boundaries and is based on a single framework runtime pattern;
- there is an obvious growth point for future document-level quality gates, HITL assembly review and persisted workflow audit;
- `AuthoringApplicationService` depends less on direct service calls and remains an orchestration layer.

Cons:

- workflow does not yet have its own persisted state/read-model layer;
- resume path currently only does baseline re-assembly, without a separate planner for selective document rewrite;
- the final artifact is still published through the existing artifact service, rather than through a separate document workflow boundary API.
