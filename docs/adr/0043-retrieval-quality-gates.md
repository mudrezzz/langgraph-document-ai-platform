# ADR-0043: Retrieval quality gates

- Status: Accepted
- Date: 2026-04-24

## Context

Production Retrieval Fabric should not only return evidence blocks, but also clearly record the weak points of the result. Low evidence count, low confidence, missing methodology/source refs and unresolved gaps have already been highlighted in the TOR and backlog. Before this, `EvidencePack.unresolved_gaps` and `confidence_notes` existed in the schema, but were not populated by the framework layer.

## Solution

1. Add `RetrievalQualityPolicy` to the framework RAG layer:
   - `min_evidence_count`;
   - `min_confidence_score`;
   - `required_document_types`.
2. Apply policy inside `EvidenceBuilder`, because it is a single build point of normalized `EvidencePack`.
3. Fill in:
   - `EvidencePack.unresolved_gaps`;
   - `EvidencePack.confidence_notes`.
4. Support gates:
   - low evidence count;
   - low confidence;
- missing required document types, including `methodology`;
   - missing source refs.
5. In retrieval task details, save:
   - `quality_gate_status`;
   - `unresolved_gaps`;
   - `confidence_notes`.
6. Release readiness report shows retrieval confidence, quality gate and unresolved gaps.

## Consequences

Pros:

- quality diagnostics become part of the existing API/evidence contract without migrations;
- authoring and MCP consumers receive unresolved gaps through the same `EvidencePack`;
- release demo can clearly show confidence and gaps;
- policy remains framework-level and is not tied to a specific domain dataset.

Cons:

- the current gate status remains advisory, workflow is not converted to failed with warning gaps;
- thresholds are currently set in bootstrap, and not in a separate runtime config object.
