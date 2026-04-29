from __future__ import annotations

from pathlib import Path

from scripts.release_decision_gate import build_release_decision_payload


def test_release_decision_payload_pass_when_smoke_and_pytest_pass(tmp_path: Path) -> None:
    payload = build_release_decision_payload(
        repo_root=tmp_path,
        gate_profile="stage",
        smoke_result={
            "status": "pass",
            "exit_code": 0,
            "payload": {"gate_status": "pass", "checks": [{"code": "RG001", "passed": True}], "failed_checks": []},
            "stdout": "",
            "stderr": "",
        },
        pytest_result={"status": "pass", "exit_code": 0, "summary_line": "=== 10 passed in 1.00s ==="},
    )
    assert payload["status"] == "pass"
    assert payload["smoke_release_gate"]["status"] == "pass"
    assert payload["test_gate_summary"]["status"] == "pass"
    assert payload["failed_checks"] == []


def test_release_decision_payload_fail_includes_failed_smoke_codes(tmp_path: Path) -> None:
    payload = build_release_decision_payload(
        repo_root=tmp_path,
        gate_profile="prod",
        smoke_result={
            "status": "fail",
            "exit_code": 1,
            "payload": {
                "gate_status": "fail",
                "checks": [{"code": "RG001", "passed": False}],
                "failed_checks": [{"code": "RG001", "name": "retrieval_events_total", "passed": False}],
            },
            "stdout": "",
            "stderr": "",
        },
        pytest_result={"status": "fail", "exit_code": 1, "summary_line": "=== 1 failed, 9 passed in 1.00s ==="},
    )
    assert payload["status"] == "fail"
    assert payload["failed_checks"][0]["code"] == "RG001"
    assert "RG001" in payload["decision_reason"]
