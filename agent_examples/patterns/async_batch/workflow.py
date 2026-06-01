from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from schemas.rag.contracts import RetrievalFilter

from agent_examples.patterns.async_batch.tools import build_batch_id, chunk_queries, normalize_queries
from agent_examples.patterns.retrieval_first.workflow import RetrievalWorkflowInput, run_retrieval_workflow


@dataclass(frozen=True)
class AsyncBatchWorkflowInput:
    queries: list[str]
    filters: RetrievalFilter
    case_dataset_id: str
    requester: str
    batch_size: int
    continue_on_error: bool


@dataclass(frozen=True)
class AsyncBatchItemResult:
    item_index: int
    batch_index: int
    query: str
    status: str
    confidence: float
    evidence_blocks: int
    unresolved_gaps: list[str]
    top_sources: list[dict[str, str]]
    error: str | None = None


@dataclass(frozen=True)
class AsyncBatchWorkflowResult:
    batch_id: str
    execution_model: str
    started_at: str
    completed_at: str
    total_queries: int
    completed_queries: int
    failed_queries: int
    items: list[AsyncBatchItemResult]


def run_async_batch_workflow(payload: AsyncBatchWorkflowInput) -> AsyncBatchWorkflowResult:
    queries = normalize_queries(payload.queries)
    if not queries:
        raise ValueError("Async batch requires at least one non-empty query.")

    started_at = datetime.now(timezone.utc).isoformat()
    batch_id = build_batch_id()
    item_results: list[AsyncBatchItemResult] = []
    item_index = 0

    for batch_index, query_chunk in enumerate(chunk_queries(queries, payload.batch_size)):
        for query in query_chunk:
            try:
                workflow_state = run_retrieval_workflow(
                    RetrievalWorkflowInput(
                        query=query,
                        filters=payload.filters,
                        case_dataset_id=payload.case_dataset_id,
                        requester=payload.requester,
                    )
                )
                evidence_pack = workflow_state.evidence_pack
                selected_blocks = [] if evidence_pack is None else evidence_pack.selected_blocks
                selected_sources = [] if evidence_pack is None else evidence_pack.selected_sources
                unresolved_gaps = [] if evidence_pack is None else evidence_pack.unresolved_gaps
                top_sources = [
                    {
                        "doc_id": source.doc_id,
                        "version": source.version,
                        "block_id": source.block_id,
                    }
                    for source in selected_sources[:3]
                ]
                item_results.append(
                    AsyncBatchItemResult(
                        item_index=item_index,
                        batch_index=batch_index,
                        query=query,
                        status="completed",
                        confidence=workflow_state.confidence,
                        evidence_blocks=len(selected_blocks),
                        unresolved_gaps=unresolved_gaps,
                        top_sources=top_sources,
                    )
                )
            except Exception as exc:
                if not payload.continue_on_error:
                    raise
                item_results.append(
                    AsyncBatchItemResult(
                        item_index=item_index,
                        batch_index=batch_index,
                        query=query,
                        status="failed",
                        confidence=0.0,
                        evidence_blocks=0,
                        unresolved_gaps=[],
                        top_sources=[],
                        error=str(exc),
                    )
                )
            item_index += 1

    completed_at = datetime.now(timezone.utc).isoformat()
    completed_queries = sum(1 for item in item_results if item.status == "completed")
    failed_queries = len(item_results) - completed_queries
    return AsyncBatchWorkflowResult(
        batch_id=batch_id,
        execution_model="in_process_framework_workflow",
        started_at=started_at,
        completed_at=completed_at,
        total_queries=len(item_results),
        completed_queries=completed_queries,
        failed_queries=failed_queries,
        items=item_results,
    )

