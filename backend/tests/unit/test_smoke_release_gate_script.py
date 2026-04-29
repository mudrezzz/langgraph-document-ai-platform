from __future__ import annotations

from scripts.smoke_release_gate import evaluate_release_gate


def test_release_gate_evaluate_passes_for_valid_payload() -> None:
    checks = evaluate_release_gate(
        retrieval_events_summary={
            "total_events": 3,
            "transitions": [
                {"from_status": None, "to_status": "running", "total": 1},
                {"from_status": "running", "to_status": "completed", "total": 1},
            ],
            "daily": [{"bucket_start": "2026-04-29T00:00:00+00:00", "total_events": 3, "unique_tasks": 1}],
            "weekly": [{"bucket_start": "2026-04-28T00:00:00+00:00", "total_events": 3, "unique_tasks": 1}],
        },
        observability={
            "total_tasks": 4,
            "daily": [{"bucket_start": "2026-04-29T00:00:00+00:00", "total_tasks": 4}],
            "weekly": [{"bucket_start": "2026-04-28T00:00:00+00:00", "total_tasks": 4}],
            "duration_sla_breaches_total": 0,
            "queue_wait_sla_breaches_total": 0,
        },
        hitl_summary={"total_actions": 2},
        authoring_status={"details": {"draft_generation_mode": "llm", "llm_tokens_total": 120}},
        require_llm_tokens=True,
        min_events_total=2,
        min_observability_total_tasks=2,
        max_duration_sla_breaches=0,
        max_queue_wait_sla_breaches=0,
    )

    assert checks
    assert all(item["passed"] for item in checks)


def test_release_gate_evaluate_fails_on_llm_tokens_and_breaches() -> None:
    checks = evaluate_release_gate(
        retrieval_events_summary={
            "total_events": 1,
            "transitions": [{"from_status": None, "to_status": "running", "total": 1}],
            "daily": [],
            "weekly": [],
        },
        observability={
            "total_tasks": 1,
            "daily": [],
            "weekly": [],
            "duration_sla_breaches_total": 3,
            "queue_wait_sla_breaches_total": 2,
        },
        hitl_summary={"total_actions": 0},
        authoring_status={"details": {"draft_generation_mode": "deterministic", "llm_tokens_total": 0}},
        require_llm_tokens=True,
        min_events_total=2,
        min_observability_total_tasks=2,
        max_duration_sla_breaches=1,
        max_queue_wait_sla_breaches=1,
    )
    failed = {item["name"] for item in checks if not item["passed"]}
    assert "retrieval_events_total" in failed
    assert "retrieval_transition_running_to_completed" in failed
    assert "observability_total_tasks" in failed
    assert "duration_sla_breaches" in failed
    assert "queue_wait_sla_breaches" in failed
    assert "hitl_actions_recorded" in failed
    assert "llm_tokens_total_non_zero" in failed
    assert "draft_generation_mode_llm" in failed
