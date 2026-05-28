from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from agent_examples.common.path_setup import ensure_backend_paths

ensure_backend_paths(repo_root=REPO_ROOT)

from agent_examples.patterns.hitl_gate.agent import HitlGateAgent
from agent_examples.patterns.hitl_gate.config import HitlGateConfig


def test_hitl_agent_formats_workflow_result(monkeypatch) -> None:
    sample_payload = {
        "artifact_title": "Demo HITL",
        "artifact_format": "markdown",
        "decision_history": [{"iteration": 1, "decision": "approve"}],
        "review_result": {"recommendation": "conditional_go"},
        "workflow_steps": [{"name": "hitl.iteration_1"}],
        "section_traceability": [{"section_id": "risk_assessment"}],
        "final_document": {"content": "X" * 450},
        "task_status": "completed",
    }
    monkeypatch.setattr("agent_examples.patterns.hitl_gate.agent.run_hitl_workflow", lambda _payload: sample_payload)
    agent = HitlGateAgent(config=HitlGateConfig())
    result = agent.run(query="q", decisions=["approve"])
    assert result["pattern"] == "hitl_gate"
    assert result["execution_model"] == "in_process_framework_workflow"
    assert result["task_status"] == "completed"
    assert result["traceability_sections"] == 1
    assert result["content_preview"].endswith("...")


def test_hitl_agent_in_process_smoke() -> None:
    agent = HitlGateAgent(config=HitlGateConfig())
    result = agent.run(decisions=["needs_changes", "approve"])
    assert result["pattern"] == "hitl_gate"
    assert result["execution_model"] == "in_process_framework_workflow"
    assert result["task_status"] == "completed"
    assert len(result["hitl_decisions_applied"]) == 2
