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

from scripts.build_binary_demo_documents import build_binary_demo_documents


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Smoke-проверка Knowledge Indexing API task lifecycle")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8075)
    parser.add_argument("--startup-timeout-sec", type=int, default=30)
    parser.add_argument(
        "--input-path",
        default="backend/examples/cases/release_go_no_go_multifile_case/input",
        help="Файл или директория документов для canonical indexing",
    )
    parser.add_argument(
        "--build-binary-demo-docs",
        action="store_true",
        help="Перед smoke сгенерировать DOCX/PDF demo input files",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    repo_root = Path(__file__).resolve().parents[2]
    backend_root = repo_root / "backend"
    input_path = (repo_root / args.input_path).resolve() if not Path(args.input_path).is_absolute() else Path(args.input_path)

    if args.build_binary_demo_docs:
        input_dir = input_path.parent if input_path.is_file() else input_path
        build_binary_demo_documents(output_dir=input_dir)

    base_url = f"http://{args.host}:{args.port}"
    env = os.environ.copy()
    env["PYTHONPATH"] = f"{backend_root}{os.pathsep}{backend_root / 'packages'}"
    async_provider = env.get("APP_ASYNC_PROVIDER", "inline").strip().lower() or "inline"

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

        start_endpoint = (
            "/api/v1/tasks/knowledge-indexing/start_async"
            if async_provider == "celery"
            else "/api/v1/tasks/knowledge-indexing/start"
        )
        start_status, start_payload = _request(
            "POST",
            f"{base_url}{start_endpoint}",
            payload={
                "source_paths": [str(input_path)],
                "task_context": {
                    "requester": "smoke-knowledge-indexing-api",
                    "knowledge_source": "canonical",
                },
            },
        )
        if start_status != 200:
            raise RuntimeError(f"Knowledge indexing start failed: status={start_status}, payload={start_payload}")

        task_id = start_payload["task_id"]
        status_code, status_payload = _wait_for_task_completion(
            base_url,
            task_id,
            timeout_sec=max(30, args.startup_timeout_sec * 2),
        )
        summary_code, summary_payload = _request(
            "GET",
            f"{base_url}/api/v1/tasks/events/summary?task_id={urllib.parse.quote(task_id)}&task_type=knowledge_indexing",
        )
        observability_code, observability_payload = _request(
            "GET",
            f"{base_url}/api/v1/tasks/observability/summary?task_type=knowledge_indexing",
        )

        if status_code != 200:
            raise RuntimeError(f"Task status failed: status={status_code}, payload={status_payload}")
        if summary_code != 200:
            raise RuntimeError(f"Task events summary failed: status={summary_code}, payload={summary_payload}")
        if observability_code != 200:
            raise RuntimeError(f"Task observability summary failed: status={observability_code}, payload={observability_payload}")

        transitions = summary_payload.get("transitions", [])
        has_completed_transition = any(
            item.get("from_status") == "running" and item.get("to_status") == "completed" for item in transitions
        )
        details = status_payload.get("details", {})
        result = {
            "base_url": base_url,
            "task_id": task_id,
            "execution_mode": async_provider,
            "async_provider": details.get("async_provider"),
            "correlation_id": details.get("correlation_id"),
            "dispatch_id": details.get("dispatch_id"),
            "queue_name": details.get("queue_name"),
            "queued_at": details.get("queued_at"),
            "started_at": details.get("started_at"),
            "completed_at": details.get("completed_at"),
            "queue_wait_ms": details.get("queue_wait_ms"),
            "start_endpoint": start_endpoint,
            "start_status": start_payload.get("status"),
            "task_status": status_payload.get("status"),
            "documents_total": details.get("documents_total"),
            "indexed_doc_ids": details.get("indexed_doc_ids", []),
            "file_types": details.get("file_types", []),
            "stored_blocks_total": details.get("stored_blocks_total"),
            "embeddings_indexed": details.get("embeddings_indexed"),
            "quality_gate_status": details.get("quality_gate_status"),
            "quality_summary": details.get("quality_summary", {}),
            "parser_quality": details.get("parser_quality", {}),
            "ocr_recovered_doc_ids": [
                doc_id
                for doc_id, summary in details.get("parser_quality", {}).items()
                if "ocr_applied" in summary.get("flags", [])
            ],
            "events_summary_total": summary_payload.get("total_events"),
            "events_summary_has_running_to_completed": has_completed_transition,
            "observability_total_tasks": observability_payload.get("total_tasks"),
            "observability_task_types": observability_payload.get("task_types", []),
        }
        print(json.dumps(result, ensure_ascii=False, indent=4))
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()


def _request(method: str, url: str, payload: dict | None = None) -> tuple[int, dict]:
    data = None
    headers: dict[str, str] = {}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json; charset=utf-8"

    req = urllib.request.Request(url=url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
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


if __name__ == "__main__":
    main()
