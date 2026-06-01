from __future__ import annotations

from dataclasses import dataclass

from schemas.rag.contracts import RetrievalFilter

from agent_examples.patterns.retrieval_first.workflow import RetrievalWorkflowInput, run_retrieval_workflow


@dataclass(frozen=True)
class FacadeWorkflowInput:
    query: str
    filters: RetrievalFilter
    case_dataset_id: str
    requester: str


def run_facade_retrieval(payload: FacadeWorkflowInput):
    """Run the same core retrieval logic independent from transport adapter."""
    return run_retrieval_workflow(
        RetrievalWorkflowInput(
            query=payload.query,
            filters=payload.filters,
            case_dataset_id=payload.case_dataset_id,
            requester=payload.requester,
        )
    )

