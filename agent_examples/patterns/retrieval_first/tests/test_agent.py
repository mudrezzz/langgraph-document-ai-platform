from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from agent_examples.common.path_setup import ensure_backend_paths

ensure_backend_paths(repo_root=REPO_ROOT)

from schemas.rag.contracts import EvidencePack, RetrievalFilter, SourceRef, RerankedBlock
from schemas.workflow.states import RetrievalWorkflowState

from agent_examples.patterns.retrieval_first.agent import RetrievalFirstAgent
from agent_examples.patterns.retrieval_first.config import RetrievalFirstConfig


def test_retrieval_agent_formats_workflow_result(monkeypatch) -> None:
    sample_state = RetrievalWorkflowState(
        query="q",
        filters=RetrievalFilter(project_id="p1"),
        confidence=0.9,
        unresolved_gaps=["gap-1"],
        evidence_pack=EvidencePack(
            selected_sources=[SourceRef(doc_id="D1", version="v1", block_id="b1")],
            selected_blocks=[
                RerankedBlock(
                    text="t",
                    source=SourceRef(doc_id="D1", version="v1", block_id="b1"),
                    score=0.9,
                )
            ],
            unresolved_gaps=["gap-1"],
            confidence_notes=["note"],
        ),
    )

    def _fake_run(_payload):
        return sample_state

    monkeypatch.setattr("agent_examples.patterns.retrieval_first.agent.run_retrieval_workflow", _fake_run)

    agent = RetrievalFirstAgent(config=RetrievalFirstConfig())
    result = agent.run(query="q")

    assert result["execution_model"] == "in_process_framework_workflow"
    assert result["evidence_blocks"] == 1
    assert result["top_sources"][0]["doc_id"] == "D1"


def test_retrieval_agent_in_process_smoke() -> None:
    agent = RetrievalFirstAgent(config=RetrievalFirstConfig())
    result = agent.run()
    assert result["pattern"] == "retrieval_first"
    assert result["execution_model"] == "in_process_framework_workflow"
    assert result["evidence_blocks"] > 0
