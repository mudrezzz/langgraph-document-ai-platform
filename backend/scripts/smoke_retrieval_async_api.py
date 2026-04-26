from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


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
        return 0, {}


def _wait_for_health(base_url: str, timeout_sec: int, process: subprocess.Popen[str]) -> None:
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
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
        time.sleep(0.25)

    raise TimeoutError("API сервер не поднялся за ожидаемое время")


def _wait_for_task_completion(base_url: str, task_id: str, timeout_sec: int) -> tuple[int, dict]:
    deadline = time.time() + timeout_sec
    last_payload: dict = {}

    while time.time() < deadline:
        status_code, status_payload = _request("GET", f"{base_url}/api/v1/tasks/{urllib.parse.quote(task_id)}")
        if status_code == 200:
            last_payload = status_payload
            if status_payload.get("status") in {"completed", "failed"}:
                return status_code, status_payload
        time.sleep(0.5)

    raise TimeoutError(f"Retrieval task {task_id} не завершился вовремя. last={last_payload}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Smoke-проверка async retrieval API flow")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8076)
    parser.add_argument("--startup-timeout-sec", type=int, default=30)
    parser.add_argument("--query", default="Что блокирует релиз и какие approvals еще не закрыты?")
    parser.add_argument("--case-dataset-id", default="saa_release_readiness")
    parser.add_argument("--case-dataset-path", default="")
    parser.add_argument("--case-dataset-dir", default="")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    repo_root = Path(__file__).resolve().parents[2]
    backend_root = repo_root / "backend"
    base_url = f"http://{args.host}:{args.port}"

    env = os.environ.copy()
    env["PYTHONPATH"] = f"{backend_root}{os.pathsep}{backend_root / 'packages'}"

    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "apps.api.main:app",
            "--host",
            args.host,
            "--port",
            str(args.port),
        ],
        cwd=str(backend_root),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    try:
        _wait_for_health(base_url, timeout_sec=args.startup_timeout_sec, process=process)

        task_context: dict[str, str] = {
            "requester": "smoke-retrieval-async-api",
            "case_dataset_id": args.case_dataset_id,
        }
        if args.case_dataset_path.strip():
            task_context["case_dataset_path"] = str(Path(args.case_dataset_path).resolve())
        if args.case_dataset_dir.strip():
            task_context["case_dataset_dir"] = str(Path(args.case_dataset_dir).resolve())

        start_status, start_payload = _request(
            "POST",
            f"{base_url}/api/v1/tasks/retrieval/start_async",
            payload={
                "query": args.query,
                "filters": {
                    "project_id": "p1",
                    "document_types": ["requirements", "methodology", "security", "operations", "governance"],
                },
                "task_context": task_context,
            },
        )
        if start_status != 200:
            raise RuntimeError(f"Async retrieval start failed: status={start_status}, payload={start_payload}")

        task_id = start_payload["task_id"]
        status_code, status_payload = _wait_for_task_completion(
            base_url,
            task_id,
            timeout_sec=max(30, args.startup_timeout_sec * 3),
        )
        evidence_code, evidence_payload = _request("GET", f"{base_url}/api/v1/tasks/{urllib.parse.quote(task_id)}/evidence")
        summary_code, summary_payload = _request(
            "GET",
            f"{base_url}/api/v1/tasks/events/summary?task_id={urllib.parse.quote(task_id)}&task_type=retrieval_pack",
        )

        if status_code != 200:
            raise RuntimeError(f"Task status failed: status={status_code}, payload={status_payload}")
        if evidence_code != 200:
            raise RuntimeError(f"Evidence failed: status={evidence_code}, payload={evidence_payload}")
        if summary_code != 200:
            raise RuntimeError(f"Task events summary failed: status={summary_code}, payload={summary_payload}")

        transitions = summary_payload.get("transitions", [])
        has_queued_to_running = any(
            item.get("from_status") == "queued" and item.get("to_status") == "running" for item in transitions
        )
        has_running_to_completed = any(
            item.get("from_status") == "running" and item.get("to_status") == "completed" for item in transitions
        )
        details = status_payload.get("details", {})
        result = {
            "base_url": base_url,
            "task_id": task_id,
            "start_status": start_payload.get("status"),
            "task_status": status_payload.get("status"),
            "execution_mode": details.get("execution_mode"),
            "knowledge_source": details.get("knowledge_source"),
            "retrieval_backend": details.get("retrieval_backend"),
            "quality_gate_status": details.get("quality_gate_status"),
            "evidence_blocks": len(evidence_payload.get("evidence_pack", {}).get("selected_blocks", [])),
            "top_sources": evidence_payload.get("evidence_pack", {}).get("selected_sources", [])[:3],
            "events_summary_total": summary_payload.get("total_events"),
            "events_summary_has_queued_to_running": has_queued_to_running,
            "events_summary_has_running_to_completed": has_running_to_completed,
        }
        print(json.dumps(result, ensure_ascii=False, indent=4))
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()


if __name__ == "__main__":
    main()
