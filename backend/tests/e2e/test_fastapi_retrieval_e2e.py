from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import pytest


@pytest.fixture(scope="module")
def server_base_url() -> str:
    """Поднимает реальный uvicorn процесс и возвращает base URL для e2e тестов."""

    repo_root = Path(__file__).resolve().parents[3]
    backend_root = repo_root / "backend"

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        _, port = sock.getsockname()

    env = os.environ.copy()
    env["PYTHONPATH"] = f"{backend_root}{os.pathsep}{backend_root / 'packages'}"

    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "apps.api.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
        ],
        cwd=str(backend_root),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    base_url = f"http://127.0.0.1:{port}"

    try:
        _wait_for_health(base_url, timeout_sec=20, process=process)
        yield base_url
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()


def _wait_for_health(base_url: str, timeout_sec: int, process: subprocess.Popen[str]) -> None:
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        # Если процесс уже завершился, сразу показываем stderr для диагностики.
        if process.poll() is not None:
            stderr = process.stderr.read().strip() if process.stderr else ""
            stdout = process.stdout.read().strip() if process.stdout else ""
            raise RuntimeError(
                "Uvicorn завершился до старта health endpoint.\n"
                f"exit_code={process.returncode}\nstdout:\n{stdout}\nstderr:\n{stderr}"
            )

        status, body = _request("GET", f"{base_url}/health")
        if status == 200 and body.get("status") == "ok":
            return
        time.sleep(0.2)

    raise TimeoutError("Сервер не поднялся за ожидаемое время")


def _request(method: str, url: str, payload: dict | None = None) -> tuple[int, dict]:
    data = None
    headers: dict[str, str] = {}

    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = urllib.request.Request(url=url, data=data, method=method, headers=headers)

    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            body = response.read().decode("utf-8")
            return response.getcode(), json.loads(body) if body else {}
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8")
        return exc.code, json.loads(body) if body else {}
    except urllib.error.URLError:
        # Сетевые ошибки (например, connection refused) возвращаем как "нет ответа".
        return 0, {}


def _start_task(base_url: str) -> str:
    status, body = _request(
        "POST",
        f"{base_url}/api/v1/tasks/retrieval/start",
        payload={
            "query": "релиз ограничения approval",
            "filters": {
                "project_id": "p1",
                "document_types": ["requirements", "methodology", "security", "operations", "governance"],
            },
            "task_context": {
                "requester": "e2e-test",
                "case_dataset_id": "saa_release_readiness",
            },
        },
    )

    assert status == 200
    return body["task_id"]


def _start_task_with_dataset_path(base_url: str) -> str:
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

    status, body = _request(
        "POST",
        f"{base_url}/api/v1/tasks/retrieval/start",
        payload={
            "query": "release approval constraints",
            "filters": {
                "project_id": "p1",
                "document_types": ["requirements", "methodology", "security", "operations", "governance"],
            },
            "task_context": {
                "requester": "e2e-test-dataset-path",
                "case_dataset_path": str(dataset_path),
            },
        },
    )

    assert status == 200
    return body["task_id"]


def _start_task_with_dataset_dir(base_url: str) -> str:
    repo_root = Path(__file__).resolve().parents[3]
    dataset_dir = (
        repo_root
        / "backend"
        / "examples"
        / "cases"
        / "release_go_no_go_multifile_case"
        / "input"
    )

    status, body = _request(
        "POST",
        f"{base_url}/api/v1/tasks/retrieval/start",
        payload={
            "query": "что блокирует релиз и какие approvals pending",
            "filters": {
                "project_id": "p1",
                "document_types": ["requirements", "methodology", "security", "operations", "governance"],
            },
            "task_context": {
                "requester": "e2e-test-dataset-dir",
                "case_dataset_dir": str(dataset_dir),
            },
        },
    )

    assert status == 200
    return body["task_id"]


def _start_authoring_task(base_url: str) -> str:
    status, body = _request(
        "POST",
        f"{base_url}/api/v1/tasks/authoring/start",
        payload={
            "query": "подготовь release readiness draft",
            "filters": {
                "project_id": "p1",
                "document_types": ["requirements", "methodology", "security", "operations", "governance"],
            },
            "task_context": {
                "requester": "e2e-authoring-test",
                "case_dataset_id": "saa_release_readiness",
            },
            "artifact_type": "release_report",
            "artifact_title": "E2E Authoring Draft",
            "artifact_format": "markdown",
            "draft_strategy": "deterministic",
            "workflow_mode": "multi_step",
        },
    )

    assert status == 200
    return body["task_id"]


def _start_authoring_task_async(base_url: str, *, hitl_required: bool = True) -> str:
    status, body = _request(
        "POST",
        f"{base_url}/api/v1/tasks/authoring/start_async",
        payload={
            "query": "подготовь async release readiness draft",
            "filters": {
                "project_id": "p1",
                "document_types": ["requirements", "methodology", "security", "operations", "governance"],
            },
            "task_context": {
                "requester": "e2e-authoring-async-test",
                "case_dataset_id": "saa_release_readiness",
            },
            "artifact_type": "release_report",
            "artifact_title": "E2E Async Authoring Draft",
            "artifact_format": "markdown",
            "draft_strategy": "deterministic",
            "workflow_mode": "multi_step",
            "hitl_required": hitl_required,
        },
    )

    assert status == 200
    assert body["status"] == "queued"
    return body["task_id"]


def test_e2e_health_endpoint(server_base_url: str) -> None:
    status, body = _request("GET", f"{server_base_url}/health")

    assert status == 200
    assert body["status"] == "ok"


def test_e2e_start_endpoint(server_base_url: str) -> None:
    task_id = _start_task(server_base_url)

    assert task_id


def test_e2e_start_endpoint_supports_case_dataset_path(server_base_url: str) -> None:
    task_id = _start_task_with_dataset_path(server_base_url)

    assert task_id


def test_e2e_start_endpoint_supports_case_dataset_dir(server_base_url: str) -> None:
    task_id = _start_task_with_dataset_dir(server_base_url)

    assert task_id


def test_e2e_status_endpoint(server_base_url: str) -> None:
    task_id = _start_task(server_base_url)

    status, body = _request("GET", f"{server_base_url}/api/v1/tasks/{task_id}")

    assert status == 200
    assert body["status"] == "completed"


def test_e2e_tasks_history_endpoint(server_base_url: str) -> None:
    task_id_1 = _start_task(server_base_url)
    task_id_2 = _start_task(server_base_url)

    status, body = _request("GET", f"{server_base_url}/api/v1/tasks?limit=1")

    assert status == 200
    assert body["total_returned"] == 1
    assert body["has_more"] is True
    assert body["next_cursor"]

    next_cursor = body["next_cursor"]
    status_2, body_2 = _request("GET", f"{server_base_url}/api/v1/tasks?limit=20&cursor={next_cursor}")
    assert status_2 == 200

    task_ids = {item["task_id"] for item in body["items"] + body_2["items"]}
    assert task_id_1 in task_ids
    assert task_id_2 in task_ids


def test_e2e_task_events_endpoint(server_base_url: str) -> None:
    task_id = _start_task(server_base_url)

    status, body = _request("GET", f"{server_base_url}/api/v1/tasks/events?limit=1&task_id={task_id}")
    assert status == 200
    assert body["total_returned"] == 1
    assert body["items"][0]["task_id"] == task_id
    assert body["items"][0]["to_status"] in {"running", "completed"}
    assert body["next_cursor"]

    status_2, body_2 = _request(
        "GET",
        f"{server_base_url}/api/v1/tasks/events?limit=20&task_id={task_id}&cursor={body['next_cursor']}",
    )
    assert status_2 == 200
    assert body_2["total_returned"] >= 1

    status_3, body_3 = _request(
        "GET",
        f"{server_base_url}/api/v1/tasks/events?limit=20&task_id={task_id}&from_status=running&to_status=completed",
    )
    assert status_3 == 200
    assert body_3["total_returned"] == 1
    assert body_3["items"][0]["from_status"] == "running"
    assert body_3["items"][0]["to_status"] == "completed"


def test_e2e_task_events_summary_endpoint(server_base_url: str) -> None:
    task_id = _start_task(server_base_url)

    status, body = _request(
        "GET",
        f"{server_base_url}/api/v1/tasks/events/summary?task_id={task_id}&task_type=retrieval_pack",
    )
    assert status == 200
    assert body["total_events"] >= 2
    assert body["unique_tasks"] == 1
    transitions = {(item["from_status"], item["to_status"]) for item in body["transitions"]}
    assert (None, "running") in transitions
    assert ("running", "completed") in transitions


def test_e2e_evidence_endpoint(server_base_url: str) -> None:
    task_id = _start_task(server_base_url)

    status, body = _request("GET", f"{server_base_url}/api/v1/tasks/{task_id}/evidence")

    assert status == 200
    assert body["task_id"] == task_id
    assert len(body["evidence_pack"]["selected_blocks"]) >= 1


def test_e2e_resume_endpoint(server_base_url: str) -> None:
    task_id = _start_task(server_base_url)

    status, body = _request(
        "POST",
        f"{server_base_url}/api/v1/tasks/{task_id}/resume",
        payload={
            "decision": "rerun",
            "comment": "e2e rerun",
            "metadata": {"source": "e2e-test"},
        },
    )

    assert status == 200
    assert body["status"] == "completed"
    assert body["details"]["resume_decision"] == "rerun"


def test_e2e_authoring_start_and_artifact_endpoint(server_base_url: str) -> None:
    task_id = _start_authoring_task(server_base_url)

    status_code, status_payload = _request("GET", f"{server_base_url}/api/v1/tasks/{task_id}")
    assert status_code == 200
    assert status_payload["status"] == "completed"
    assert status_payload["details"]["artifact_id"]
    assert status_payload["details"]["current_step"] == "completed"
    assert status_payload["details"]["workflow_mode"] == "multi_step"
    assert len(status_payload["details"]["steps_summary"]) == 4

    artifact_code, artifact_payload = _request("GET", f"{server_base_url}/api/v1/tasks/{task_id}/artifact")
    assert artifact_code == 200
    assert artifact_payload["task_id"] == task_id
    assert artifact_payload["artifact_type"] == "release_report"
    assert artifact_payload["title"] == "E2E Authoring Draft"
    assert artifact_payload["metadata"]["draft_generation_mode"] in {"deterministic", "deterministic_fallback"}
    assert artifact_payload["metadata"]["workflow_mode"] == "multi_step"
    assert len(artifact_payload["metadata"]["steps_summary"]) == 4
    assert len(artifact_payload["traceability"]["source_refs"]) >= 1
    assert len(artifact_payload["traceability"]["sections"]) >= 3


def test_e2e_authoring_async_hitl_flow(server_base_url: str) -> None:
    task_id = _start_authoring_task_async(server_base_url, hitl_required=True)

    status_payload = {}
    for _ in range(40):
        status_code, status_payload = _request("GET", f"{server_base_url}/api/v1/tasks/{task_id}")
        assert status_code == 200
        if status_payload["status"] in {"waiting_human", "completed", "failed"}:
            break
        time.sleep(0.1)

    assert status_payload["status"] == "waiting_human"

    hitl_code, hitl_payload = _request("GET", f"{server_base_url}/api/v1/tasks/{task_id}/hitl")
    assert hitl_code == 200
    assert hitl_payload["required"] is True

    submit_code, submit_payload = _request(
        "POST",
        f"{server_base_url}/api/v1/tasks/{task_id}/hitl/submit",
        payload={
            "decision": "approve",
            "comment": "e2e reviewer approved",
            "metadata": {"source": "e2e-authoring-async-test"},
            "idempotency_key": "e2e-approve-1",
            "expected_iteration": 1,
        },
    )
    assert submit_code == 200
    assert submit_payload["status"] in {"queued", "running", "completed"}

    final_payload: dict = submit_payload
    for _ in range(40):
        status_code, final_payload = _request("GET", f"{server_base_url}/api/v1/tasks/{task_id}")
        assert status_code == 200
        if final_payload["status"] in {"completed", "failed"}:
            break
        time.sleep(0.1)
    assert final_payload["status"] == "completed"

    artifact_code, artifact_payload = _request("GET", f"{server_base_url}/api/v1/tasks/{task_id}/artifact")
    assert artifact_code == 200
    assert artifact_payload["metadata"]["hitl_decision"] == "approve"
    assert artifact_payload["metadata"]["hitl_iteration"] == 1
    assert len(artifact_payload["traceability"]["sections"]) >= 3

    actions_code, actions_payload = _request("GET", f"{server_base_url}/api/v1/hitl/actions?task_id={task_id}")
    assert actions_code == 200
    assert actions_payload["total_returned"] >= 1
