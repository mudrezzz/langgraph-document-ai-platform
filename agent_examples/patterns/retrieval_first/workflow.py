from __future__ import annotations

from dataclasses import dataclass

from domain_rag.retrieval import build_retrieval_workflow
from schemas.rag.contracts import RetrievalFilter
from schemas.workflow.states import RetrievalWorkflowState


@dataclass(frozen=True)
class RetrievalWorkflowInput:
    query: str
    filters: RetrievalFilter
    case_dataset_id: str
    requester: str


def run_retrieval_workflow(payload: RetrievalWorkflowInput) -> RetrievalWorkflowState:
    """Run retrieval workflow directly in-process.

    This is the key difference from transport-first demos: we do not call HTTP API,
    we execute framework/domain workflow as a Python library composition.
    """

    workflow = build_retrieval_workflow(case_dataset_id=payload.case_dataset_id)
    initial_state = RetrievalWorkflowState(
        query=payload.query,
        filters=payload.filters,
        task_context={"requester": payload.requester, "case_dataset_id": payload.case_dataset_id},
    )
    return workflow.invoke(initial_state)
