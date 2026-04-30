from __future__ import annotations

import json
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
AGENT_EXAMPLES_ROOT = REPO_ROOT / "agent_examples"


def test_agent_examples_contains_required_structure() -> None:
    required_paths = [
        "agent_examples/README.md",
        "agent_examples/run_example.py",
        "agent_examples/common/framework_client.py",
        "agent_examples/common/runtime.py",
        "agent_examples/patterns/retrieval_first/agent.py",
        "agent_examples/patterns/retrieval_first/README.md",
        "agent_examples/patterns/authoring_first/agent.py",
        "agent_examples/patterns/authoring_first/README.md",
        "agent_examples/patterns/hitl_gate/agent.py",
        "agent_examples/patterns/hitl_gate/README.md",
    ]
    for path in required_paths:
        assert (REPO_ROOT / path).exists(), path


def test_run_example_dry_run_returns_pattern_payload() -> None:
    python_bin = REPO_ROOT / ".venv" / "bin" / "python"
    completed = subprocess.run(
        [
            str(python_bin),
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
    assert payload["base_url"].startswith("http://")
