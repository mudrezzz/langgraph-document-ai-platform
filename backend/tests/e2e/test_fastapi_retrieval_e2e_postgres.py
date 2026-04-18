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
    return shutil.which("docker") is not None


@pytest.fixture(scope="module")
def postgres_backed_server_base_url() -> str:
    """Поднимает PostgreSQL через docker compose и запускает API с реальным APP_DB_DSN."""

    if not _docker_available():
        pytest.skip("Docker не установлен, e2e postgres test пропускается")

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

        yield base_url
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


def test_e2e_postgres_health_endpoint(postgres_backed_server_base_url: str) -> None:
    status, body = _request("GET", f"{postgres_backed_server_base_url}/health")

    assert status == 200
    assert body["status"] == "ok"


def test_e2e_postgres_task_flow(postgres_backed_server_base_url: str) -> None:
    task_id = _start_task(postgres_backed_server_base_url)

    status_code, status_payload = _request(
        "GET", f"{postgres_backed_server_base_url}/api/v1/tasks/{task_id}"
    )
    assert status_code == 200
    assert status_payload["status"] == "completed"

    evidence_code, evidence_payload = _request(
        "GET", f"{postgres_backed_server_base_url}/api/v1/tasks/{task_id}/evidence"
    )
    assert evidence_code == 200
    assert len(evidence_payload["evidence_pack"]["selected_blocks"]) >= 1

    resume_code, resume_payload = _request(
        "POST",
        f"{postgres_backed_server_base_url}/api/v1/tasks/{task_id}/resume",
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
        "GET", f"{postgres_backed_server_base_url}/api/v1/tasks?limit=20&offset=0"
    )
    assert history_code == 200
    assert history_payload["total_returned"] >= 1
    task_ids = {item["task_id"] for item in history_payload["items"]}
    assert task_id in task_ids
