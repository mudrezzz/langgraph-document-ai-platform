from __future__ import annotations

import json

import pytest

from examples.quickstart_agents import (
    EXAMPLE_REGISTRY,
    ExampleNotFoundError,
    build_example_command,
    get_example_spec,
    list_examples,
)


def test_example_registry_contains_expected_quickstart_cases() -> None:
    assert {
        "retrieval_faq_assistant",
        "authoring_policy_brief",
        "hitl_review_loop",
    }.issubset(set(EXAMPLE_REGISTRY))


def test_list_examples_returns_json_serializable_payload() -> None:
    payload = {"examples": list_examples()}
    raw = json.dumps(payload, ensure_ascii=False)
    assert "retrieval_faq_assistant" in raw
    assert "Authoring-First Agent" in raw


def test_build_example_command_linux_uses_shell_script() -> None:
    command = build_example_command("retrieval_faq_assistant", platform_hint="linux")
    assert command[0] == "bash"
    assert command[1].endswith("backend/scripts/smoke_retrieval_api.sh")
    assert "--query" in command


def test_build_example_command_windows_uses_powershell_script() -> None:
    command = build_example_command("authoring_policy_brief", platform_hint="windows")
    assert command[0] == "pwsh"
    assert command[1] == "-File"
    assert command[2].endswith("backend/scripts/smoke_authoring_api.ps1")


def test_build_example_command_appends_extra_args() -> None:
    command = build_example_command(
        "hitl_review_loop",
        platform_hint="linux",
        extra_args=("--port", "9250"),
    )
    assert command[-2:] == ["--port", "9250"]


def test_get_example_spec_raises_for_unknown_id() -> None:
    with pytest.raises(ExampleNotFoundError):
        get_example_spec("unknown_case")
