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


def test_e2e_health_endpoint(server_base_url: str) -> None:
    status, body = _request("GET", f"{server_base_url}/health")

    assert status == 200
    assert body["status"] == "ok"


def test_e2e_start_endpoint(server_base_url: str) -> None:
    task_id = _start_task(server_base_url)

    assert task_id


def test_e2e_status_endpoint(server_base_url: str) -> None:
    task_id = _start_task(server_base_url)

    status, body = _request("GET", f"{server_base_url}/api/v1/tasks/{task_id}")

    assert status == 200
    assert body["status"] == "completed"


def test_e2e_tasks_history_endpoint(server_base_url: str) -> None:
    task_id_1 = _start_task(server_base_url)
    task_id_2 = _start_task(server_base_url)

    status, body = _request("GET", f"{server_base_url}/api/v1/tasks?limit=20&offset=0")

    assert status == 200
    assert body["total_returned"] >= 2
    task_ids = {item["task_id"] for item in body["items"]}
    assert task_id_1 in task_ids
    assert task_id_2 in task_ids


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
