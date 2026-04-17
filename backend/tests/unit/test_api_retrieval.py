from fastapi.testclient import TestClient

from apps.api.main import app


def test_retrieval_api_start_status_evidence_flow() -> None:
    client = TestClient(app)

    start_response = client.post(
        "/api/v1/tasks/retrieval/start",
        json={
            "query": "evidence pack retrieval",
            "filters": {
                "project_id": "p1",
                "document_types": ["requirements", "methodology"],
            },
            "task_context": {"requester": "unit-test"},
        },
    )

    assert start_response.status_code == 200
    task_id = start_response.json()["task_id"]

    status_response = client.get(f"/api/v1/tasks/{task_id}")
    assert status_response.status_code == 200
    assert status_response.json()["status"] == "completed"

    evidence_response = client.get(f"/api/v1/tasks/{task_id}/evidence")
    assert evidence_response.status_code == 200
    assert len(evidence_response.json()["evidence_pack"]["selected_blocks"]) >= 1


def test_retrieval_api_resume_rerun_flow() -> None:
    client = TestClient(app)

    start_response = client.post(
        "/api/v1/tasks/retrieval/start",
        json={
            "query": "langgraph retrieval",
            "filters": {"project_id": "p1"},
            "task_context": {},
        },
    )

    task_id = start_response.json()["task_id"]

    resume_response = client.post(
        f"/api/v1/tasks/{task_id}/resume",
        json={
            "decision": "rerun",
            "comment": "run once more",
            "metadata": {"requested_by": "qa"},
        },
    )

    assert resume_response.status_code == 200
    assert resume_response.json()["status"] == "completed"
    assert resume_response.json()["details"]["resume_decision"] == "rerun"


def test_retrieval_api_not_found() -> None:
    client = TestClient(app)
    response = client.get("/api/v1/tasks/missing-task")

    assert response.status_code == 404