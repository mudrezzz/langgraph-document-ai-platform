from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import time
from urllib.parse import quote

import pytest
from fastapi.testclient import TestClient

from application.knowledge_indexing_service import KnowledgeIndexingApplicationService
from apps.api.dependencies import get_container
from apps.api.main import app


@pytest.fixture(autouse=True)
def reset_api_container() -> None:
    """Сбрасываем singleton-контейнер между тестами, чтобы не протекало состояние."""

    get_container.cache_clear()
    yield
    get_container.cache_clear()


@pytest.fixture()
def client() -> TestClient:
    """Создает тестовый HTTP-клиент FastAPI."""

    return TestClient(app)


def _create_task(client: TestClient) -> str:
    response = client.post(
        "/api/v1/tasks/retrieval/start",
        json={
            "query": "evidence pack retrieval",
            "filters": {
                "project_id": "p1",
                "document_types": ["requirements", "methodology"],
            },
            "task_context": {"requester": "integration-test"},
        },
    )

    assert response.status_code == 200
    payload = response.json()
    return payload["task_id"]


def _create_interrupted_task(client: TestClient) -> str:
    response = client.post(
        "/api/v1/tasks/retrieval/start",
        json={
            "query": "needs human gate",
            "filters": {"project_id": "p1"},
            "task_context": {"force_interrupt": True},
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "interrupted"
    return payload["task_id"]


def _create_authoring_task(client: TestClient) -> str:
    response = client.post(
        "/api/v1/tasks/authoring/start",
        json={
            "query": "подготовь черновик release readiness и traceability",
            "filters": {"project_id": "p1"},
            "task_context": {"requester": "integration-authoring-test"},
            "artifact_type": "release_report",
            "artifact_title": "Integration Authoring Draft",
            "artifact_format": "markdown",
            "draft_strategy": "deterministic",
            "workflow_mode": "multi_step",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    return payload["task_id"]


def _create_authoring_task_async(client: TestClient, *, hitl_required: bool = True) -> str:
    response = client.post(
        "/api/v1/tasks/authoring/start_async",
        json={
            "query": "подготовь async черновик release readiness и traceability",
            "filters": {"project_id": "p1"},
            "task_context": {"requester": "integration-authoring-async-test"},
            "artifact_type": "release_report",
            "artifact_title": "Integration Async Authoring Draft",
            "artifact_format": "markdown",
            "draft_strategy": "deterministic",
            "workflow_mode": "multi_step",
            "hitl_required": hitl_required,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    return payload["task_id"]


def test_health_endpoint_returns_ok(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_start_endpoint_returns_task_id(client: TestClient) -> None:
    response = client.post(
        "/api/v1/tasks/retrieval/start",
        json={
            "query": "langgraph retrieval",
            "filters": {"project_id": "p1"},
            "task_context": {},
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "completed"
    assert body["task_id"]


def test_start_endpoint_persists_task_id_in_task_context(client: TestClient) -> None:
    task_id = _create_task(client)

    payload = get_container().task_service.get_state_payload(task_id)

    assert payload["task_context"]["task_id"] == task_id


def test_start_endpoint_returns_400_for_empty_query(client: TestClient) -> None:
    response = client.post(
        "/api/v1/tasks/retrieval/start",
        json={
            "query": "   ",
            "filters": {"project_id": "p1"},
            "task_context": {},
        },
    )

    assert response.status_code == 400


def test_start_endpoint_supports_case_dataset_path(client: TestClient) -> None:
    repo_root = Path(__file__).resolve().parents[3]
    dataset_path = (
        repo_root
        / "backend"
        / "examples"
        / "cases"
        / "saa_release_readiness_case"
        / "input"
        / "knowledge_layers.json"
    )

    response = client.post(
        "/api/v1/tasks/retrieval/start",
        json={
            "query": "release approval constraints",
            "filters": {"project_id": "p1"},
            "task_context": {
                "case_dataset_path": str(dataset_path),
                "requester": "integration-path-test",
            },
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "completed"


def test_start_endpoint_supports_case_dataset_dir(client: TestClient) -> None:
    repo_root = Path(__file__).resolve().parents[3]
    dataset_dir = (
        repo_root
        / "backend"
        / "examples"
        / "cases"
        / "release_go_no_go_multifile_case"
        / "input"
    )

    response = client.post(
        "/api/v1/tasks/retrieval/start",
        json={
            "query": "что блокирует релиз и какие approvals pending",
            "filters": {"project_id": "p1"},
            "task_context": {
                "case_dataset_dir": str(dataset_dir),
                "requester": "integration-dir-test",
            },
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "completed"


def test_start_endpoint_supports_canonical_knowledge_source(client: TestClient) -> None:
    repo_root = Path(__file__).resolve().parents[3]
    dataset_dir = (
        repo_root
        / "backend"
        / "examples"
        / "cases"
        / "release_go_no_go_multifile_case"
        / "input"
    )
    container = get_container()
    indexing_result = KnowledgeIndexingApplicationService(
        canonical_document_service=container.canonical_document_service
    ).index_paths([dataset_dir])

    response = client.post(
        "/api/v1/tasks/retrieval/start",
        json={
            "query": "что блокирует релиз и какие approvals pending",
            "filters": {"project_id": "p1"},
            "task_context": {
                "knowledge_source": "canonical",
                "canonical_doc_ids": indexing_result.indexed_doc_ids,
                "requester": "integration-canonical-knowledge-test",
            },
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "completed"

    task_status = client.get(f"/api/v1/tasks/{payload['task_id']}").json()
    assert task_status["details"]["knowledge_source"] == "canonical"


def test_knowledge_indexing_endpoint_records_task_lifecycle(client: TestClient) -> None:
    repo_root = Path(__file__).resolve().parents[3]
    dataset_dir = (
        repo_root
        / "backend"
        / "examples"
        / "cases"
        / "release_go_no_go_multifile_case"
        / "input"
    )

    response = client.post(
        "/api/v1/tasks/knowledge-indexing/start",
        json={
            "source_paths": [str(dataset_dir)],
            "task_context": {"requester": "integration-knowledge-indexing-test"},
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "completed"

    task_status = client.get(f"/api/v1/tasks/{payload['task_id']}").json()
    details = task_status["details"]
    assert task_status["status"] == "completed"
    assert details["documents_total"] == 6
    assert details["file_types"] == ["docx", "json", "md", "pdf", "txt"]
    assert details["stored_blocks_total"] >= 8
    assert details["quality_gate_status"] in {"passed", "warning"}
    assert details["quality_summary"]["quality_flags_total"] >= 0

    summary_response = client.get(
        f"/api/v1/tasks/events/summary?task_id={quote(payload['task_id'])}&task_type=knowledge_indexing"
    )
    assert summary_response.status_code == 200
    transitions = summary_response.json()["transitions"]
    assert any(
        item["from_status"] == "running" and item["to_status"] == "completed"
        for item in transitions
    )


def test_status_endpoint_returns_task_state(client: TestClient) -> None:
    task_id = _create_task(client)

    response = client.get(f"/api/v1/tasks/{task_id}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["task_id"] == task_id
    assert payload["status"] == "completed"


def test_tasks_history_endpoint_supports_cursor_pagination(client: TestClient) -> None:
    task_id_1 = _create_task(client)
    task_id_2 = _create_task(client)

    first_response = client.get("/api/v1/tasks?limit=1")
    assert first_response.status_code == 200

    first_payload = first_response.json()
    assert first_payload["limit"] == 1
    assert first_payload["total_returned"] == 1
    assert first_payload["has_more"] is True
    assert first_payload["next_cursor"]

    second_response = client.get(f"/api/v1/tasks?limit=10&cursor={quote(first_payload['next_cursor'])}")
    assert second_response.status_code == 200
    second_payload = second_response.json()

    ids = {item["task_id"] for item in first_payload["items"] + second_payload["items"]}
    assert task_id_1 in ids
    assert task_id_2 in ids


def test_tasks_history_endpoint_applies_filters(client: TestClient) -> None:
    completed_task_id = _create_task(client)
    interrupted_task_id = _create_interrupted_task(client)

    completed = client.get("/api/v1/tasks?limit=20&status=completed")
    assert completed.status_code == 200
    completed_ids = {item["task_id"] for item in completed.json()["items"]}
    assert completed_task_id in completed_ids
    assert interrupted_task_id not in completed_ids

    interrupted = client.get("/api/v1/tasks?limit=20&status=interrupted")
    assert interrupted.status_code == 200
    interrupted_ids = {item["task_id"] for item in interrupted.json()["items"]}
    assert interrupted_task_id in interrupted_ids
    assert completed_task_id not in interrupted_ids

    task_type_filtered = client.get("/api/v1/tasks?limit=20&task_type=retrieval_pack")
    assert task_type_filtered.status_code == 200
    assert task_type_filtered.json()["total_returned"] >= 2

    now_utc = datetime.now(timezone.utc)
    from_param = quote((now_utc - timedelta(minutes=5)).isoformat())
    to_param = quote((now_utc + timedelta(minutes=5)).isoformat())
    ranged = client.get(f"/api/v1/tasks?limit=20&from={from_param}&to={to_param}")
    assert ranged.status_code == 200
    ranged_ids = {item["task_id"] for item in ranged.json()["items"]}
    assert completed_task_id in ranged_ids
    assert interrupted_task_id in ranged_ids


def test_tasks_history_endpoint_returns_400_for_invalid_cursor(client: TestClient) -> None:
    response = client.get("/api/v1/tasks?limit=20&cursor=invalid_cursor_payload")

    assert response.status_code == 400


def test_tasks_history_endpoint_validates_limit(client: TestClient) -> None:
    response = client.get("/api/v1/tasks?limit=0")

    assert response.status_code == 422


def test_task_events_endpoint_supports_cursor_and_filters(client: TestClient) -> None:
    task_id = _create_task(client)

    first_response = client.get("/api/v1/tasks/events?limit=1")
    assert first_response.status_code == 200
    first_payload = first_response.json()
    assert first_payload["limit"] == 1
    assert first_payload["total_returned"] == 1
    assert first_payload["items"][0]["task_id"] == task_id
    assert first_payload["next_cursor"] is not None
    assert first_payload["has_more"] is True

    second_response = client.get(f"/api/v1/tasks/events?limit=20&cursor={quote(first_payload['next_cursor'])}")
    assert second_response.status_code == 200
    second_payload = second_response.json()
    assert second_payload["total_returned"] >= 1

    filtered = client.get(f"/api/v1/tasks/events?limit=20&task_id={task_id}&task_type=retrieval_pack")
    assert filtered.status_code == 200
    filtered_payload = filtered.json()
    assert filtered_payload["total_returned"] >= 4
    assert {item["task_id"] for item in filtered_payload["items"]} == {task_id}
    node_events = [
        item for item in filtered_payload["items"] if item["event_payload"].get("event_kind") == "workflow_node"
    ]
    assert {(item["event_payload"]["node_name"], item["event_payload"]["node_status"]) for item in node_events} == {
        ("invoke_entry", "started"),
        ("invoke_entry", "completed"),
    }

    now_utc = datetime.now(timezone.utc)
    from_param = quote((now_utc - timedelta(minutes=5)).isoformat())
    to_param = quote((now_utc + timedelta(minutes=5)).isoformat())
    ranged = client.get(f"/api/v1/tasks/events?limit=20&from={from_param}&to={to_param}")
    assert ranged.status_code == 200
    assert ranged.json()["total_returned"] >= 2

    completed_only = client.get(
        f"/api/v1/tasks/events?limit=20&task_id={task_id}&from_status=running&to_status=completed"
    )
    assert completed_only.status_code == 200
    completed_payload = completed_only.json()
    assert completed_payload["total_returned"] == 1
    assert completed_payload["items"][0]["from_status"] == "running"
    assert completed_payload["items"][0]["to_status"] == "completed"


def test_task_events_summary_endpoint_returns_aggregates(client: TestClient) -> None:
    task_id = _create_task(client)

    response = client.get(
        f"/api/v1/tasks/events/summary?task_id={task_id}&task_type=retrieval_pack"
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["total_events"] >= 2
    assert payload["unique_tasks"] == 1

    transitions = {
        (item["from_status"], item["to_status"]): item["total"]
        for item in payload["transitions"]
    }
    assert transitions[(None, "running")] >= 1
    assert transitions[("running", "completed")] >= 1


def test_task_events_endpoint_returns_400_for_invalid_cursor(client: TestClient) -> None:
    response = client.get("/api/v1/tasks/events?limit=20&cursor=invalid_cursor_payload")

    assert response.status_code == 400


def test_status_endpoint_returns_404_for_unknown_task(client: TestClient) -> None:
    response = client.get("/api/v1/tasks/unknown")

    assert response.status_code == 404


def test_evidence_endpoint_returns_evidence_pack(client: TestClient) -> None:
    task_id = _create_task(client)

    response = client.get(f"/api/v1/tasks/{task_id}/evidence")

    assert response.status_code == 200
    payload = response.json()
    assert payload["task_id"] == task_id
    assert len(payload["evidence_pack"]["selected_blocks"]) >= 1


def test_evidence_endpoint_uses_realistic_case_dataset(client: TestClient) -> None:
    response = client.post(
        "/api/v1/tasks/retrieval/start",
        json={
            "query": "ограничения релиза и approval",
            "filters": {
                "project_id": "p1",
                "document_types": ["requirements", "methodology", "security", "operations", "governance"],
            },
            "task_context": {
                "case_dataset_id": "saa_release_readiness",
                "requester": "integration-test",
            },
        },
    )
    assert response.status_code == 200
    task_id = response.json()["task_id"]

    evidence_response = client.get(f"/api/v1/tasks/{task_id}/evidence")
    assert evidence_response.status_code == 200
    payload = evidence_response.json()

    doc_ids = {item["doc_id"] for item in payload["evidence_pack"]["selected_sources"]}
    assert "METH-001" in doc_ids
    assert "GOV-021" in doc_ids


def test_evidence_endpoint_returns_404_for_unknown_task(client: TestClient) -> None:
    response = client.get("/api/v1/tasks/unknown/evidence")

    assert response.status_code == 404


def test_evidence_endpoint_returns_409_for_interrupted_task_without_evidence(client: TestClient) -> None:
    task_id = _create_interrupted_task(client)

    response = client.get(f"/api/v1/tasks/{task_id}/evidence")

    assert response.status_code == 409


def test_resume_endpoint_returns_completed_status(client: TestClient) -> None:
    task_id = _create_task(client)

    response = client.post(
        f"/api/v1/tasks/{task_id}/resume",
        json={
            "decision": "rerun",
            "comment": "integration rerun",
            "metadata": {"source": "integration-test"},
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "completed"
    assert payload["details"]["resume_decision"] == "rerun"


def test_resume_endpoint_can_complete_interrupted_task(client: TestClient) -> None:
    task_id = _create_interrupted_task(client)

    response = client.post(
        f"/api/v1/tasks/{task_id}/resume",
        json={
            "decision": "continue",
            "comment": "approved by reviewer",
            "metadata": {"reviewer": "integration-test"},
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "completed"
    assert payload["details"]["resume_decision"] == "continue"


def test_resume_endpoint_returns_404_for_unknown_task(client: TestClient) -> None:
    response = client.post(
        "/api/v1/tasks/unknown/resume",
        json={
            "decision": "rerun",
            "comment": "integration rerun",
            "metadata": {"source": "integration-test"},
        },
    )

    assert response.status_code == 404


def test_authoring_start_endpoint_returns_task_id(client: TestClient) -> None:
    task_id = _create_authoring_task(client)

    status_response = client.get(f"/api/v1/tasks/{task_id}")
    assert status_response.status_code == 200
    payload = status_response.json()
    assert payload["status"] == "completed"
    assert payload["details"]["artifact_id"]
    assert payload["details"]["retrieval_task_id"]
    assert payload["details"]["current_step"] == "completed"
    assert payload["details"]["workflow_mode"] == "multi_step"
    assert len(payload["details"]["steps_summary"]) == 4


def test_task_artifact_endpoint_returns_authoring_artifact(client: TestClient) -> None:
    task_id = _create_authoring_task(client)

    response = client.get(f"/api/v1/tasks/{task_id}/artifact")

    assert response.status_code == 200
    payload = response.json()
    assert payload["task_id"] == task_id
    assert payload["artifact_type"] == "release_report"
    assert payload["title"] == "Integration Authoring Draft"
    assert len(payload["content"]) >= 10
    assert payload["metadata"]["draft_generation_mode"] in {"deterministic", "deterministic_fallback"}
    assert payload["metadata"]["workflow_mode"] == "multi_step"
    assert payload["metadata"]["review_status"] in {"completed", "needs_revision", "skipped"}
    assert len(payload["metadata"]["steps_summary"]) == 4
    assert payload["traceability"]["retrieval_task_id"]
    assert len(payload["traceability"]["source_refs"]) >= 1
    assert len(payload["traceability"]["sections"]) >= 3


def test_task_artifact_endpoint_returns_json_artifact_when_requested(client: TestClient) -> None:
    response = client.post(
        "/api/v1/tasks/authoring/start",
        json={
            "query": "подготовь board memo в json",
            "filters": {"project_id": "p1"},
            "task_context": {
                "requester": "integration-authoring-json-test",
                "template_id": "board_memo",
                "template_payload": {
                    "sections": [
                        {
                            "section_id": "decision",
                            "title": "Decision",
                            "objective": "Summarize board decision.",
                            "required_keywords": ["approval", "decision"],
                        }
                    ],
                    "assembly_rules": [
                        {
                            "rule_id": "board_json",
                            "mode": "section_order",
                            "section_order": ["decision"],
                            "include_writer_draft": False,
                            "include_traceability": False,
                        }
                    ],
                },
            },
            "artifact_type": "board_memo",
            "artifact_title": "Integration Board Memo JSON",
            "artifact_format": "json",
            "draft_strategy": "deterministic",
            "workflow_mode": "multi_step",
        },
    )

    assert response.status_code == 200
    task_id = response.json()["task_id"]

    artifact = client.get(f"/api/v1/tasks/{task_id}/artifact")
    assert artifact.status_code == 200
    payload = artifact.json()
    assert payload["format"] == "json"
    assert payload["metadata"]["export_format_resolved"] == "json"
    assert '"sections"' in payload["content"]
    assert '"writer_draft"' not in payload["content"]
    assert '"traceability"' not in payload["content"]


def test_task_artifact_endpoint_returns_409_for_non_authoring_task(client: TestClient) -> None:
    retrieval_task_id = _create_task(client)

    response = client.get(f"/api/v1/tasks/{retrieval_task_id}/artifact")

    assert response.status_code == 409


def test_task_artifact_endpoint_returns_404_for_unknown_task(client: TestClient) -> None:
    response = client.get("/api/v1/tasks/unknown/artifact")

    assert response.status_code == 404


def test_authoring_hitl_status_returns_outline_snapshot(client: TestClient) -> None:
    task_id = _create_authoring_task_async(client, hitl_required=True)

    status_payload: dict = {}
    for _ in range(20):
        response = client.get(f"/api/v1/tasks/{task_id}")
        assert response.status_code == 200
        status_payload = response.json()
        if status_payload["status"] in {"waiting_human", "completed", "failed"}:
            break
        time.sleep(0.05)

    assert status_payload["status"] == "waiting_human"
    hitl_status = client.get(f"/api/v1/tasks/{task_id}/hitl")
    assert hitl_status.status_code == 200
    payload = hitl_status.json()
    assert payload["phase"] == "outline_review"
    assert payload["outline"]["template_id"] == "release_readiness"
    assert payload["outline"]["sections"][0]["section_id"] == "risk_assessment"
    assert payload["outline"]["sections"][0]["source_refs"]


def test_authoring_async_endpoint_and_hitl_submit_flow(client: TestClient) -> None:
    task_id = _create_authoring_task_async(client, hitl_required=True)

    status_payload: dict = {}
    for _ in range(20):
        response = client.get(f"/api/v1/tasks/{task_id}")
        assert response.status_code == 200
        status_payload = response.json()
        if status_payload["status"] in {"waiting_human", "completed", "failed"}:
            break
        time.sleep(0.05)

    assert status_payload["status"] == "waiting_human"
    hitl_status = client.get(f"/api/v1/tasks/{task_id}/hitl")
    assert hitl_status.status_code == 200
    hitl_payload = hitl_status.json()
    assert hitl_payload["required"] is True
    assert hitl_payload["status"] == "waiting_human"
    assert hitl_payload["current_iteration"] == 1
    assert hitl_payload["max_iterations"] >= 1

    submit = client.post(
        f"/api/v1/tasks/{task_id}/hitl/submit",
        json={
            "decision": "approve",
            "comment": "integration reviewer approved",
            "metadata": {"reviewer": "integration"},
            "idempotency_key": "integration-approve-1",
            "expected_iteration": 1,
        },
    )
    assert submit.status_code == 200
    submit_payload = submit.json()
    assert submit_payload["status"] in {"queued", "running", "completed"}

    final_payload: dict = submit_payload
    for _ in range(30):
        response = client.get(f"/api/v1/tasks/{task_id}")
        assert response.status_code == 200
        final_payload = response.json()
        if final_payload["status"] in {"completed", "failed"}:
            break
        time.sleep(0.05)
    assert final_payload["status"] == "completed"

    artifact = client.get(f"/api/v1/tasks/{task_id}/artifact")
    assert artifact.status_code == 200
    artifact_payload = artifact.json()
    assert artifact_payload["metadata"]["hitl_decision"] == "approve"
    assert artifact_payload["metadata"]["workflow_mode"] == "multi_step"
    assert artifact_payload["metadata"]["hitl_iteration"] == 1
    assert len(artifact_payload["traceability"]["sections"]) >= 3

    actions_response = client.get(f"/api/v1/hitl/actions?task_id={task_id}&decision=approve")
    assert actions_response.status_code == 200
    actions_payload = actions_response.json()
    assert actions_payload["total_returned"] >= 1
    assert actions_payload["items"][0]["decision"] == "approve"


def test_authoring_hitl_iterative_needs_changes_flow(client: TestClient) -> None:
    task_id = _create_authoring_task_async(client, hitl_required=True)

    first_wait_payload: dict = {}
    for _ in range(20):
        response = client.get(f"/api/v1/tasks/{task_id}")
        assert response.status_code == 200
        first_wait_payload = response.json()
        if first_wait_payload["status"] in {"waiting_human", "completed", "failed"}:
            break
        time.sleep(0.05)
    assert first_wait_payload["status"] == "waiting_human"

    first_submit = client.post(
        f"/api/v1/tasks/{task_id}/hitl/submit",
        json={
            "decision": "needs_changes",
            "comment": "дополни pending approvals",
            "metadata": {"reviewer": "integration"},
            "idempotency_key": "integration-needs-changes-1",
            "expected_iteration": 1,
        },
    )
    assert first_submit.status_code == 200

    second_wait_payload: dict = {}
    for _ in range(30):
        response = client.get(f"/api/v1/tasks/{task_id}")
        assert response.status_code == 200
        second_wait_payload = response.json()
        if second_wait_payload["status"] in {"waiting_human", "completed", "failed"}:
            break
        time.sleep(0.05)
    assert second_wait_payload["status"] == "waiting_human"
    assert second_wait_payload["details"]["hitl_iteration"] == 2

    replay = client.post(
        f"/api/v1/tasks/{task_id}/hitl/submit",
        json={
            "decision": "needs_changes",
            "comment": "дополни pending approvals",
            "metadata": {"reviewer": "integration"},
            "idempotency_key": "integration-needs-changes-1",
            "expected_iteration": 2,
        },
    )
    assert replay.status_code == 200
    replay_payload = replay.json()
    assert replay_payload["status"] == "waiting_human"

    invalid = client.post(
        f"/api/v1/tasks/{task_id}/hitl/submit",
        json={
            "decision": "needs_changes",
            "comment": "еще правки",
            "expected_iteration": 2,
        },
    )
    assert invalid.status_code == 409

    approve = client.post(
        f"/api/v1/tasks/{task_id}/hitl/submit",
        json={
            "decision": "approve",
            "comment": "финально ок",
            "metadata": {"reviewer": "integration"},
            "idempotency_key": "integration-approve-2",
            "expected_iteration": 2,
        },
    )
    assert approve.status_code == 200

    final_payload: dict = {}
    for _ in range(30):
        response = client.get(f"/api/v1/tasks/{task_id}")
        assert response.status_code == 200
        final_payload = response.json()
        if final_payload["status"] in {"completed", "failed"}:
            break
        time.sleep(0.05)
    assert final_payload["status"] == "completed"

    hitl_status = client.get(f"/api/v1/tasks/{task_id}/hitl")
    assert hitl_status.status_code == 200
    hitl_payload = hitl_status.json()
    assert hitl_payload["current_iteration"] == 2
    assert len(hitl_payload["actions"]) == 2

    actions_history = client.get(
        f"/api/v1/hitl/actions?task_id={task_id}&reviewer=integration&limit=10"
    )
    assert actions_history.status_code == 200
    history_payload = actions_history.json()
    assert history_payload["total_returned"] == 2
    decisions = {item["decision"] for item in history_payload["items"]}
    assert decisions == {"needs_changes", "approve"}


def test_hitl_actions_endpoint_returns_400_for_invalid_cursor(client: TestClient) -> None:
    response = client.get("/api/v1/hitl/actions?cursor=invalid_cursor_payload")
    assert response.status_code == 400


def test_authoring_async_endpoint_can_complete_without_hitl(client: TestClient) -> None:
    task_id = _create_authoring_task_async(client, hitl_required=False)

    status_payload: dict = {}
    for _ in range(20):
        response = client.get(f"/api/v1/tasks/{task_id}")
        assert response.status_code == 200
        status_payload = response.json()
        if status_payload["status"] in {"completed", "failed"}:
            break
        time.sleep(0.05)

    assert status_payload["status"] == "completed"
