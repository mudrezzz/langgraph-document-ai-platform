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
        result = subprocess.run(["docker", "info"], capture_output=True, text=True, timeout=10, check=False)
        return result.returncode == 0
    except Exception:
        return False


def _request(method: str, url: str, payload: dict | None = None) -> tuple[int, dict]:
    data = None
    headers: dict[str, str] = {}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = urllib.request.Request(url=url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            body = response.read().decode("utf-8")
            return response.getcode(), json.loads(body) if body else {}
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8")
        return exc.code, json.loads(body) if body else {}
    except urllib.error.URLError:
        return 0, {}


def _pick_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


@pytest.fixture(scope="module")
def celery_async_server_base_url() -> str:
    if not _docker_available() or os.getenv("RUN_DOCKER_ASYNC_E2E", "0").strip() != "1":
        pytest.skip("Для async celery e2e требуется Docker и RUN_DOCKER_ASYNC_E2E=1")

    repo_root = Path(__file__).resolve().parents[3]
    backend_root = repo_root / "backend"
    postgres_compose = backend_root / "docker-compose.postgres.yml"
    async_compose = backend_root / "docker-compose.async.yml"
    env_path = backend_root / ".env"

    postgres_project = f"lg-async-pg-{uuid.uuid4().hex[:8]}"
    async_project = f"lg-async-queue-{uuid.uuid4().hex[:8]}"
    postgres_port = _pick_free_port()
    redis_port = _pick_free_port()
    app_db_dsn = f"postgresql://app:app@127.0.0.1:{postgres_port}/langgraph"

    # Поднимаем PostgreSQL для persistence.
    postgres_env = os.environ.copy()
    postgres_env["POSTGRES_PORT"] = str(postgres_port)
    subprocess.run(
        [
            "docker",
            "compose",
            "-f",
            str(postgres_compose),
            "--project-name",
            postgres_project,
            "--env-file",
            str(env_path),
            "up",
            "-d",
        ],
        cwd=str(backend_root),
        env=postgres_env,
        check=True,
    )

    # Применяем миграции к PostgreSQL на хосте.
    migrate_env = os.environ.copy()
    migrate_env["APP_DB_DSN"] = app_db_dsn
    migrate_env["APP_DB_SCHEMA"] = "app"
    migrate_cmd = ["bash", str(backend_root / "scripts" / "apply_migrations.sh")]
    migrate_deadline = time.time() + 45
    while True:
        migrate_result = subprocess.run(
            migrate_cmd,
            cwd=str(repo_root),
            env=migrate_env,
            capture_output=True,
            text=True,
            check=False,
        )
        if migrate_result.returncode == 0:
            break
        if time.time() >= migrate_deadline:
            raise RuntimeError(
                "Не удалось применить миграции в async celery e2e.\n"
                f"stdout:\n{migrate_result.stdout}\n"
                f"stderr:\n{migrate_result.stderr}"
            )
        time.sleep(1.0)

    # Поднимаем Redis + Celery worker.
    async_env = os.environ.copy()
    async_env["REDIS_PORT"] = str(redis_port)
    async_env["APP_WORKER_DB_DSN"] = f"postgresql://app:app@host.docker.internal:{postgres_port}/langgraph"
    subprocess.run(
        [
            "docker",
            "compose",
            "-f",
            str(async_compose),
            "--project-name",
            async_project,
            "--env-file",
            str(env_path),
            "up",
            "-d",
            "--build",
        ],
        cwd=str(backend_root),
        env=async_env,
        check=True,
    )

    port = _pick_free_port()

    env = os.environ.copy()
    env["PYTHONPATH"] = f"{backend_root}{os.pathsep}{backend_root / 'packages'}"
    env["APP_RUNTIME_PROFILE"] = "prod"
    env["APP_DB_DSN"] = app_db_dsn
    env["APP_DB_SCHEMA"] = "app"
    env["APP_ASYNC_PROVIDER"] = "celery"
    env["APP_CELERY_BROKER_URL"] = f"redis://127.0.0.1:{redis_port}/0"
    env["APP_CELERY_RESULT_BACKEND"] = f"redis://127.0.0.1:{redis_port}/0"
    env["APP_CELERY_QUEUE"] = "authoring"

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

    deadline = time.time() + 30
    while time.time() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"uvicorn exited early: {process.stderr.read() if process.stderr else ''}")
        code, payload = _request("GET", f"{base_url}/health")
        if code == 200 and payload.get("status") == "ok":
            break
        time.sleep(0.3)
    else:
        raise TimeoutError("API не поднялся для async celery e2e")

    try:
        yield base_url
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()

        subprocess.run(
            [
                "docker",
                "compose",
                "-f",
                str(async_compose),
                "--project-name",
                async_project,
                "down",
                "--volumes",
            ],
            cwd=str(backend_root),
            check=False,
        )
        subprocess.run(
            [
                "docker",
                "compose",
                "-f",
                str(postgres_compose),
                "--project-name",
                postgres_project,
                "down",
                "--volumes",
            ],
            cwd=str(backend_root),
            check=False,
        )


def test_e2e_async_authoring_with_celery_and_hitl(celery_async_server_base_url: str) -> None:
    base_url = celery_async_server_base_url

    start_code, start_payload = _request(
        "POST",
        f"{base_url}/api/v1/tasks/authoring/start_async",
        payload={
            "query": "подготовь async draft с ручным review",
            "filters": {
                "project_id": "p1",
                "document_types": ["requirements", "methodology", "security", "operations", "governance"],
            },
            "task_context": {"requester": "e2e-celery", "case_dataset_id": "saa_release_readiness"},
            "artifact_type": "release_report",
            "artifact_title": "Async Celery E2E Draft",
            "artifact_format": "markdown",
            "draft_strategy": "deterministic",
            "workflow_mode": "multi_step",
            "hitl_required": True,
        },
    )
    assert start_code == 200
    assert start_payload["status"] == "queued"
    task_id = start_payload["task_id"]

    status_payload: dict = {}
    for _ in range(120):
        status_code, status_payload = _request("GET", f"{base_url}/api/v1/tasks/{task_id}")
        assert status_code == 200
        if status_payload["status"] in {"waiting_human", "completed", "failed"}:
            break
        time.sleep(0.5)

    assert status_payload["status"] == "waiting_human"

    submit_code, submit_payload = _request(
        "POST",
        f"{base_url}/api/v1/tasks/{task_id}/hitl/submit",
        payload={
            "decision": "approve",
            "comment": "async celery e2e approve",
            "metadata": {"source": "e2e-celery"},
            "idempotency_key": "e2e-celery-approve-1",
            "expected_iteration": 1,
        },
    )
    assert submit_code == 200
    assert submit_payload["status"] in {"queued", "running", "completed"}

    final_payload: dict = submit_payload
    for _ in range(120):
        status_code, final_payload = _request("GET", f"{base_url}/api/v1/tasks/{task_id}")
        assert status_code == 200
        if final_payload["status"] in {"completed", "failed"}:
            break
        time.sleep(0.5)
    assert final_payload["status"] == "completed"

    artifact_code, artifact_payload = _request("GET", f"{base_url}/api/v1/tasks/{task_id}/artifact")
    assert artifact_code == 200
    assert artifact_payload["metadata"]["hitl_decision"] == "approve"
    assert artifact_payload["metadata"]["hitl_iteration"] == 1
    assert len(artifact_payload["traceability"]["sections"]) >= 3
