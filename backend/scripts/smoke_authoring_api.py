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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Smoke-проверка authoring API flow")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8030)
    parser.add_argument("--startup-timeout-sec", type=int, default=30)
    parser.add_argument("--query", default="подготовь release readiness draft и traceability")
    parser.add_argument("--artifact-type", default="release_report")
    parser.add_argument("--artifact-title", default="Smoke Authoring Draft")
    parser.add_argument("--artifact-format", default="markdown")
    parser.add_argument("--draft-strategy", default="auto", choices=["auto", "deterministic", "llm"])
    parser.add_argument("--require-llm", action="store_true")
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
            "requester": "smoke-authoring-api",
            "case_dataset_id": args.case_dataset_id,
        }
        if args.case_dataset_path.strip():
            task_context["case_dataset_path"] = str(Path(args.case_dataset_path).resolve())
        if args.case_dataset_dir.strip():
            task_context["case_dataset_dir"] = str(Path(args.case_dataset_dir).resolve())

        start_status, start_payload = _request(
            "POST",
            f"{base_url}/api/v1/tasks/authoring/start",
            payload={
                "query": args.query,
                "filters": {
                    "project_id": "p1",
                    "document_types": ["requirements", "methodology", "security", "operations", "governance"],
                },
                "task_context": task_context,
                "artifact_type": args.artifact_type,
                "artifact_title": args.artifact_title,
                "artifact_format": args.artifact_format,
                "draft_strategy": args.draft_strategy,
            },
        )
        if start_status != 200:
            raise RuntimeError(f"Authoring start failed: status={start_status}, payload={start_payload}")

        task_id = start_payload["task_id"]
        status_code, status_payload = _request("GET", f"{base_url}/api/v1/tasks/{task_id}")
        artifact_code, artifact_payload = _request("GET", f"{base_url}/api/v1/tasks/{task_id}/artifact")
        summary_code, summary_payload = _request(
            "GET",
            f"{base_url}/api/v1/tasks/events/summary?task_id={urllib.parse.quote(task_id)}&task_type=authoring_pack",
        )

        if status_code != 200:
            raise RuntimeError(f"Task status failed: status={status_code}, payload={status_payload}")
        if artifact_code != 200:
            raise RuntimeError(f"Task artifact failed: status={artifact_code}, payload={artifact_payload}")
        if summary_code != 200:
            raise RuntimeError(f"Task events summary failed: status={summary_code}, payload={summary_payload}")

        transitions = summary_payload.get("transitions", [])
        has_completed_transition = any(
            item.get("from_status") == "running" and item.get("to_status") == "completed" for item in transitions
        )
        generation_mode = artifact_payload.get("metadata", {}).get("draft_generation_mode")

        if args.require_llm and generation_mode != "llm":
            raise RuntimeError(
                f"Ожидался llm draft_generation_mode, получено: {generation_mode}. "
                f"artifact_metadata={artifact_payload.get('metadata')}"
            )

        result = {
            "base_url": base_url,
            "task_id": task_id,
            "start_status": start_payload.get("status"),
            "task_status": status_payload.get("status"),
            "artifact_id": artifact_payload.get("artifact_id"),
            "artifact_type": artifact_payload.get("artifact_type"),
            "artifact_title": artifact_payload.get("title"),
            "draft_generation_mode": generation_mode,
            "draft_model_provider": artifact_payload.get("metadata", {}).get("draft_model_provider"),
            "draft_model_name": artifact_payload.get("metadata", {}).get("draft_model_name"),
            "traceability_sources": len(artifact_payload.get("traceability", {}).get("source_refs", [])),
            "events_summary_total": summary_payload.get("total_events"),
            "events_summary_has_running_to_completed": has_completed_transition,
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
