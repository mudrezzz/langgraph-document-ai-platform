from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
AGENT_EXAMPLES_ROOT = REPO_ROOT / "agent_examples"


def _resolve_python_bin() -> str:
    candidates = [
        REPO_ROOT / ".venv" / "bin" / "python",
        REPO_ROOT / ".venv" / "Scripts" / "python.exe",
        Path(sys.executable),
    ]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    return "python"


def test_agent_examples_contains_required_structure() -> None:
    required_paths = [
        "agent_examples/README.md",
        "agent_examples/run_example.py",
        "agent_examples/tests/run_harness.py",
        "agent_examples/common/framework_client.py",
        "agent_examples/common/path_setup.py",
        "agent_examples/common/runtime.py",
        "agent_examples/patterns/retrieval_first/agent.py",
        "agent_examples/patterns/retrieval_first/workflow.py",
        "agent_examples/patterns/retrieval_first/tools.py",
        "agent_examples/patterns/retrieval_first/main.py",
        "agent_examples/patterns/retrieval_first/tests/test_agent.py",
        "agent_examples/patterns/retrieval_first/expected_output/result.example.json",
        "agent_examples/patterns/retrieval_first/README.md",
        "agent_examples/patterns/authoring_first/agent.py",
        "agent_examples/patterns/authoring_first/workflow.py",
        "agent_examples/patterns/authoring_first/tools.py",
        "agent_examples/patterns/authoring_first/main.py",
        "agent_examples/patterns/authoring_first/tests/test_agent.py",
        "agent_examples/patterns/authoring_first/expected_output/result.example.json",
        "agent_examples/patterns/authoring_first/README.md",
        "agent_examples/patterns/hitl_gate/agent.py",
        "agent_examples/patterns/hitl_gate/workflow.py",
        "agent_examples/patterns/hitl_gate/tools.py",
        "agent_examples/patterns/hitl_gate/main.py",
        "agent_examples/patterns/hitl_gate/tests/test_agent.py",
        "agent_examples/patterns/hitl_gate/expected_output/result.example.json",
        "agent_examples/patterns/hitl_gate/README.md",
    ]
    for path in required_paths:
        assert (REPO_ROOT / path).exists(), path


def test_run_example_dry_run_returns_pattern_payload() -> None:
    python_bin = _resolve_python_bin()
    completed = subprocess.run(
        [
            python_bin,
            str(AGENT_EXAMPLES_ROOT / "run_example.py"),
            "--pattern",
            "retrieval_first",
            "--dry-run",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(completed.stdout)
    assert payload["pattern"] == "retrieval_first"
    assert payload["mode"] == "dry_run"
    assert payload["execution_model"] == "in_process_framework_workflow"


def test_retrieval_pattern_main_runs_in_process() -> None:
    python_bin = _resolve_python_bin()
    completed = subprocess.run(
        [
            python_bin,
            str(AGENT_EXAMPLES_ROOT / "patterns" / "retrieval_first" / "main.py"),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(completed.stdout)
    assert payload["pattern"] == "retrieval_first"
    assert payload["execution_model"] == "in_process_framework_workflow"
    assert payload["evidence_blocks"] > 0


def test_authoring_pattern_main_runs_in_process() -> None:
    python_bin = _resolve_python_bin()
    completed = subprocess.run(
        [
            python_bin,
            str(AGENT_EXAMPLES_ROOT / "patterns" / "authoring_first" / "main.py"),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(completed.stdout)
    assert payload["pattern"] == "authoring_first"
    assert payload["execution_model"] == "in_process_framework_workflow"
    assert payload["section_artifacts_total"] > 0


def test_hitl_pattern_main_runs_in_process() -> None:
    python_bin = _resolve_python_bin()
    completed = subprocess.run(
        [
            python_bin,
            str(AGENT_EXAMPLES_ROOT / "patterns" / "hitl_gate" / "main.py"),
            "--hitl-decisions",
            "needs_changes,approve",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(completed.stdout)
    assert payload["pattern"] == "hitl_gate"
    assert payload["execution_model"] == "in_process_framework_workflow"
    assert payload["task_status"] == "completed"
