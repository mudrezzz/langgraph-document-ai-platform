from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

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


def test_status_endpoint_returns_task_state(client: TestClient) -> None:
    task_id = _create_task(client)

    response = client.get(f"/api/v1/tasks/{task_id}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["task_id"] == task_id
    assert payload["status"] == "completed"


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
