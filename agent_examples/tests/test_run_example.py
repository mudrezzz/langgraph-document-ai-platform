from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from agent_examples.run_example import PATTERN_CHOICES, PATTERN_INDEX, parse_hitl_decisions


def test_pattern_index_matches_choices() -> None:
    assert set(PATTERN_CHOICES) == set(PATTERN_INDEX)
    assert PATTERN_INDEX["retrieval_first"].execution_model == "in_process_framework_workflow"
    assert PATTERN_INDEX["authoring_first"].execution_model == "in_process_framework_workflow"
    assert PATTERN_INDEX["hitl_gate"].execution_model == "in_process_framework_workflow"


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("approve", ["approve"]),
        ("needs_changes,approve", ["needs_changes", "approve"]),
        (" reject , approve ", ["reject", "approve"]),
    ],
)
def test_parse_hitl_decisions_accepts_valid_values(raw: str, expected: list[str]) -> None:
    assert parse_hitl_decisions(raw) == expected


def test_parse_hitl_decisions_rejects_invalid_values() -> None:
    with pytest.raises(ValueError):
        parse_hitl_decisions("approve,maybe")
