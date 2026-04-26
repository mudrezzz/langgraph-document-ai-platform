from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path

import pytest


def _docker_available() -> bool:
    if shutil.which("docker") is None:
        return False

    try:
        result = subprocess.run(
            ["docker", "info"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        return result.returncode == 0
    except Exception:
        return False


@pytest.fixture(scope="module")
def postgres_backed_server_context() -> dict[str, str]:
    """Поднимает PostgreSQL через docker compose и запускает API с реальным APP_DB_DSN."""

    if not _docker_available():
        pytest.skip("Docker daemon недоступен, e2e postgres test пропускается")

    repo_root = Path(__file__).resolve().parents[3]
    backend_root = repo_root / "backend"
    compose_file = backend_root / "docker-compose.postgres.yml"

    if not compose_file.exists():
        pytest.skip("docker-compose.postgres.yml не найден")

    project_name = f"lg-e2e-{uuid.uuid4().hex[:8]}"

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        _, postgres_port = sock.getsockname()

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        _, api_port = sock.getsockname()

    dsn = f"postgresql://app:app@127.0.0.1:{postgres_port}/langgraph"

    compose_env = os.environ.copy()
    compose_env["POSTGRES_PORT"] = str(postgres_port)

    up_cmd = [
        "docker",
        "compose",
        "-f",
        str(compose_file),
        "--project-name",
        project_name,
        "up",
        "-d",
    ]
    down_cmd = [
        "docker",
        "compose",
        "-f",
        str(compose_file),
        "--project-name",
        project_name,
        "down",
        "-v",
    ]

    api_process: subprocess.Popen[str] | None = None

    try:
        subprocess.run(up_cmd, check=True, cwd=str(backend_root), env=compose_env, capture_output=True, text=True)
        _wait_for_postgres(dsn, timeout_sec=60)

        app_env = os.environ.copy()
        app_env["PYTHONPATH"] = f"{backend_root}{os.pathsep}{backend_root / 'packages'}"
        app_env["APP_DB_DSN"] = dsn
        app_env["APP_DB_SCHEMA"] = "app"

        subprocess.run(
            [sys.executable, str(backend_root / "scripts" / "apply_migrations.py")],
            check=True,
            cwd=str(backend_root),
            env=app_env,
            capture_output=True,
            text=True,
        )

        api_process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "apps.api.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                str(api_port),
            ],
            cwd=str(backend_root),
            env=app_env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        base_url = f"http://127.0.0.1:{api_port}"
        _wait_for_health(base_url, timeout_sec=30, process=api_process)

        yield {"base_url": base_url, "dsn": dsn}
    finally:
        if api_process is not None:
            api_process.terminate()
            try:
                api_process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                api_process.kill()

        subprocess.run(down_cmd, cwd=str(backend_root), env=compose_env, capture_output=True, text=True)


def _wait_for_postgres(dsn: str, timeout_sec: int) -> None:
    deadline = time.time() + timeout_sec

    while time.time() < deadline:
        try:
            import psycopg

            with psycopg.connect(dsn, connect_timeout=2) as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
                    _ = cur.fetchone()
                    return
        except Exception:
            time.sleep(0.5)

    raise TimeoutError("PostgreSQL не поднялся за ожидаемое время")


def _wait_for_health(base_url: str, timeout_sec: int, process: subprocess.Popen[str]) -> None:
    deadline = time.time() + timeout_sec

    while time.time() < deadline:
        # Если uvicorn упал до готовности /health, показываем stderr/stdout.
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

    raise TimeoutError("API сервер не поднялся за ожидаемое время")


def _request(method: str, url: str, payload: dict | None = None) -> tuple[int, dict]:
    data = None
    headers: dict[str, str] = {}

    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json; charset=utf-8"

    req = urllib.request.Request(url=url, data=data, method=method, headers=headers)

    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            body = response.read().decode("utf-8")
            return response.getcode(), json.loads(body) if body else {}
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8")
        return exc.code, json.loads(body) if body else {}
    except urllib.error.URLError:
        # Пока сервер стартует, connection refused считаем временным состоянием.
        return 0, {}


def _start_task(base_url: str) -> str:
    status, body = _request(
        "POST",
        f"{base_url}/api/v1/tasks/retrieval/start",
        payload={
            "query": "ограничения и approval перед релизом",
            "filters": {
                "project_id": "p1",
                "document_types": ["requirements", "methodology", "security", "operations", "governance"],
            },
            "task_context": {
                "requester": "e2e-postgres",
                "case_dataset_id": "saa_release_readiness",
            },
        },
    )

    assert status == 200
    assert body["status"] in {"completed", "interrupted"}
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
                "requester": "e2e-postgres-dataset-dir",
                "case_dataset_dir": str(dataset_dir),
            },
        },
    )

    assert status == 200
    assert body["status"] == "completed"
    return body["task_id"]


def _start_authoring_task(base_url: str) -> str:
    status, body = _request(
        "POST",
        f"{base_url}/api/v1/tasks/authoring/start",
        payload={
            "query": "подготовь authoring draft с traceability",
            "filters": {
                "project_id": "p1",
                "document_types": ["requirements", "methodology", "security", "operations", "governance"],
            },
            "task_context": {
                "requester": "e2e-postgres-authoring",
                "case_dataset_id": "saa_release_readiness",
            },
            "artifact_type": "release_report",
            "artifact_title": "Postgres E2E Draft",
            "artifact_format": "markdown",
            "draft_strategy": "deterministic",
            "workflow_mode": "multi_step",
        },
    )

    assert status == 200
    assert body["status"] == "completed"
    return body["task_id"]


def _start_authoring_task_async(base_url: str, *, hitl_required: bool = True) -> str:
    status, body = _request(
        "POST",
        f"{base_url}/api/v1/tasks/authoring/start_async",
        payload={
            "query": "подготовь async authoring draft с traceability",
            "filters": {
                "project_id": "p1",
                "document_types": ["requirements", "methodology", "security", "operations", "governance"],
            },
            "task_context": {
                "requester": "e2e-postgres-authoring-async",
                "case_dataset_id": "saa_release_readiness",
            },
            "artifact_type": "release_report",
            "artifact_title": "Postgres E2E Async Draft",
            "artifact_format": "markdown",
            "draft_strategy": "deterministic",
            "workflow_mode": "multi_step",
            "hitl_required": hitl_required,
        },
    )

    assert status == 200
    assert body["status"] == "queued"
    return body["task_id"]


def _has_langgraph_checkpoint_for_task(dsn: str, task_id: str) -> bool:
    import psycopg

    with psycopg.connect(dsn, connect_timeout=5) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM app.langgraph_checkpoints WHERE thread_id = %s LIMIT 1",
                (task_id,),
            )
            return cur.fetchone() is not None


def _has_task_artifact_link(dsn: str, task_id: str) -> bool:
    import psycopg

    with psycopg.connect(dsn, connect_timeout=5) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM app.task_artifacts WHERE task_id = %s LIMIT 1",
                (task_id,),
            )
            return cur.fetchone() is not None


def _count_hitl_actions(dsn: str, task_id: str) -> int:
    import psycopg

    with psycopg.connect(dsn, connect_timeout=5) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) FROM app.hitl_actions WHERE task_id = %s",
                (task_id,),
            )
            row = cur.fetchone()
            return int(row[0]) if row is not None else 0


def test_e2e_postgres_health_endpoint(postgres_backed_server_context: dict[str, str]) -> None:
    base_url = postgres_backed_server_context["base_url"]
    status, body = _request("GET", f"{base_url}/health")

    assert status == 200
    assert body["status"] == "ok"


def test_e2e_postgres_task_flow(postgres_backed_server_context: dict[str, str]) -> None:
    base_url = postgres_backed_server_context["base_url"]
    dsn = postgres_backed_server_context["dsn"]
    task_id = _start_task(base_url)

    status_code, status_payload = _request(
        "GET", f"{base_url}/api/v1/tasks/{task_id}"
    )
    assert status_code == 200
    assert status_payload["status"] == "completed"

    evidence_code, evidence_payload = _request(
        "GET", f"{base_url}/api/v1/tasks/{task_id}/evidence"
    )
    assert evidence_code == 200
    assert len(evidence_payload["evidence_pack"]["selected_blocks"]) >= 1

    resume_code, resume_payload = _request(
        "POST",
        f"{base_url}/api/v1/tasks/{task_id}/resume",
        payload={
            "decision": "rerun",
            "comment": "postgres e2e rerun",
            "metadata": {"source": "e2e-postgres"},
        },
    )
    assert resume_code == 200
    assert resume_payload["status"] == "completed"
    assert resume_payload["details"]["resume_decision"] == "rerun"

    history_code, history_payload = _request(
        "GET", f"{base_url}/api/v1/tasks?limit=20&status=completed&task_type=retrieval_pack"
    )
    assert history_code == 200
    assert history_payload["total_returned"] >= 1
    task_ids = {item["task_id"] for item in history_payload["items"]}
    assert task_id in task_ids

    events_code, events_payload = _request(
        "GET",
        f"{base_url}/api/v1/tasks/events?limit=20&task_id={task_id}&task_type=retrieval_pack",
    )
    assert events_code == 200
    assert events_payload["total_returned"] >= 2
    assert {item["task_id"] for item in events_payload["items"]} == {task_id}

    completed_events_code, completed_events_payload = _request(
        "GET",
        f"{base_url}/api/v1/tasks/events?limit=20&task_id={task_id}&from_status=running&to_status=completed",
    )
    assert completed_events_code == 200
    assert completed_events_payload["total_returned"] >= 1
    assert all(
        item["from_status"] == "running" and item["to_status"] == "completed"
        for item in completed_events_payload["items"]
    )

    observability_code, observability_payload = _request(
        "GET",
        f"{base_url}/api/v1/tasks/observability/summary?task_type=retrieval_pack",
    )
    assert observability_code == 200
    assert observability_payload["total_tasks"] >= 1
    assert any(item["task_type"] == "retrieval_pack" for item in observability_payload["task_types"])

    assert _has_langgraph_checkpoint_for_task(dsn=dsn, task_id=task_id) is True


def test_e2e_postgres_task_flow_supports_case_dataset_dir(postgres_backed_server_context: dict[str, str]) -> None:
    base_url = postgres_backed_server_context["base_url"]
    dsn = postgres_backed_server_context["dsn"]
    task_id = _start_task_with_dataset_dir(base_url)

    evidence_code, evidence_payload = _request("GET", f"{base_url}/api/v1/tasks/{task_id}/evidence")
    assert evidence_code == 200
    assert len(evidence_payload["evidence_pack"]["selected_blocks"]) >= 1

    assert _has_langgraph_checkpoint_for_task(dsn=dsn, task_id=task_id) is True


def test_e2e_postgres_authoring_flow(postgres_backed_server_context: dict[str, str]) -> None:
    base_url = postgres_backed_server_context["base_url"]
    dsn = postgres_backed_server_context["dsn"]
    task_id = _start_authoring_task(base_url)

    status_code, status_payload = _request("GET", f"{base_url}/api/v1/tasks/{task_id}")
    assert status_code == 200
    assert status_payload["status"] == "completed"
    assert status_payload["details"]["artifact_id"]
    assert status_payload["details"]["current_step"] == "completed"
    assert status_payload["details"]["workflow_mode"] == "multi_step"
    assert len(status_payload["details"]["steps_summary"]) == 4

    artifact_code, artifact_payload = _request("GET", f"{base_url}/api/v1/tasks/{task_id}/artifact")
    assert artifact_code == 200
    assert artifact_payload["task_id"] == task_id
    assert artifact_payload["artifact_type"] == "release_report"
    assert artifact_payload["title"] == "Postgres E2E Draft"
    assert artifact_payload["metadata"]["draft_generation_mode"] in {"deterministic", "deterministic_fallback"}
    assert artifact_payload["metadata"]["workflow_mode"] == "multi_step"
    assert len(artifact_payload["metadata"]["steps_summary"]) == 4
    assert len(artifact_payload["traceability"]["source_refs"]) >= 1
    assert len(artifact_payload["traceability"]["sections"]) >= 3

    assert _has_task_artifact_link(dsn=dsn, task_id=task_id) is True


def test_e2e_postgres_authoring_async_hitl_flow(postgres_backed_server_context: dict[str, str]) -> None:
    base_url = postgres_backed_server_context["base_url"]
    dsn = postgres_backed_server_context["dsn"]
    task_id = _start_authoring_task_async(base_url, hitl_required=True)

    status_payload: dict = {}
    for _ in range(40):
        status_code, status_payload = _request("GET", f"{base_url}/api/v1/tasks/{task_id}")
        assert status_code == 200
        if status_payload["status"] in {"waiting_human", "completed", "failed"}:
            break
        time.sleep(0.1)

    assert status_payload["status"] == "waiting_human"

    hitl_code, hitl_payload = _request("GET", f"{base_url}/api/v1/tasks/{task_id}/hitl")
    assert hitl_code == 200
    assert hitl_payload["required"] is True

    submit_code, submit_payload = _request(
        "POST",
        f"{base_url}/api/v1/tasks/{task_id}/hitl/submit",
        payload={
            "decision": "approve",
            "comment": "postgres e2e reviewer approved",
            "metadata": {"source": "e2e-postgres-authoring-async"},
            "idempotency_key": "e2e-postgres-approve-1",
            "expected_iteration": 1,
        },
    )
    assert submit_code == 200
    assert submit_payload["status"] in {"queued", "running", "completed"}

    final_payload: dict = submit_payload
    for _ in range(40):
        status_code, final_payload = _request("GET", f"{base_url}/api/v1/tasks/{task_id}")
        assert status_code == 200
        if final_payload["status"] in {"completed", "failed"}:
            break
        time.sleep(0.1)
    assert final_payload["status"] == "completed"

    artifact_code, artifact_payload = _request("GET", f"{base_url}/api/v1/tasks/{task_id}/artifact")
    assert artifact_code == 200
    assert artifact_payload["metadata"]["hitl_decision"] == "approve"
    assert artifact_payload["metadata"]["hitl_iteration"] == 1
    assert len(artifact_payload["traceability"]["sections"]) >= 3

    assert _has_task_artifact_link(dsn=dsn, task_id=task_id) is True
    assert _count_hitl_actions(dsn=dsn, task_id=task_id) >= 1
