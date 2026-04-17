from domain_rag.retrieval import build_retrieval_workflow
from schemas.rag.contracts import RetrievalFilter
from schemas.workflow.states import RetrievalWorkflowState


def test_retrieval_pack_workflow_fills_state_fields() -> None:
    workflow = build_retrieval_workflow()

    state = RetrievalWorkflowState(
        query="evidence pack",
        filters=RetrievalFilter(project_id="p1", document_types=["requirements", "methodology"]),
    )

    result = workflow.invoke(state)

    assert result.evidence_pack is not None
    assert result.confidence is not None
    assert len(result.selected_summaries) >= 1
    assert len(result.selected_blocks) >= 1
    assert len(result.reranked_blocks) >= 1


def test_retrieval_pack_workflow_resume_validates_state() -> None:
    workflow = build_retrieval_workflow()

    payload = {
        "query": "langgraph",
        "filters": {"project_id": "p1"},
    }

    resumed = workflow.resume(payload)

    assert resumed.query == "langgraph"
    assert resumed.filters.project_id == "p1"