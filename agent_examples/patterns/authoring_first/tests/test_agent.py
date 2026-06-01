from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from agent_examples.common.path_setup import ensure_backend_paths

ensure_backend_paths(repo_root=REPO_ROOT)

from agent_examples.patterns.authoring_first.agent import AuthoringFirstAgent
from agent_examples.patterns.authoring_first.config import AuthoringFirstConfig


def test_authoring_agent_formats_workflow_result(monkeypatch) -> None:
    sample_payload = {
        "workflow_mode": "multi_step",
        "draft_strategy": "deterministic",
        "artifact_title": "Demo",
        "artifact_format": "markdown",
        "review_result": {"status": "completed", "recommendation": "conditional_go"},
        "workflow_steps": [{"name": "retrieval"}, {"name": "assemble_document"}],
        "section_artifacts": [{"section_id": "risk_assessment"}],
        "section_traceability": [{"section_id": "risk_assessment"}],
        "evidence_pack": {"selected_blocks": [{"text": "b1"}]},
        "unresolved_gaps": ["gap-1"],
        "final_document": {"content": "A" * 500},
    }

    monkeypatch.setattr(
        "agent_examples.patterns.authoring_first.agent.run_authoring_workflow",
        lambda _payload: sample_payload,
    )

    agent = AuthoringFirstAgent(config=AuthoringFirstConfig())
    result = agent.run(query="q")

    assert result["pattern"] == "authoring_first"
    assert result["execution_model"] == "in_process_framework_workflow"
    assert result["review_status"] == "completed"
    assert result["recommendation"] == "conditional_go"
    assert result["traceability_sections"] == 1
    assert result["evidence_blocks"] == 1
    assert result["content_preview"].endswith("...")


def test_authoring_agent_in_process_smoke() -> None:
    agent = AuthoringFirstAgent(config=AuthoringFirstConfig())
    result = agent.run()
    assert result["pattern"] == "authoring_first"
    assert result["execution_model"] == "in_process_framework_workflow"
    assert result["section_artifacts_total"] > 0
    assert result["traceability_sections"] > 0
