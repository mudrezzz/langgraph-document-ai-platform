from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

QUERY = "Что блокирует релиз Payments v2 и какие approvals еще не закрыты?"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Async release go/no-go demo via retrieval execution plane")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8023)
    parser.add_argument("--startup-timeout-sec", type=int, default=30)
    parser.add_argument("--query", default=QUERY)
    parser.add_argument(
        "--dataset-path",
        default="backend/examples/cases/release_go_no_go_case/output/release_packet_dataset.generated.json",
    )
    parser.add_argument(
        "--output-file",
        default="backend/examples/cases/release_go_no_go_case/output/release_readiness_report_async.md",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    repo_root = Path(__file__).resolve().parents[2]
    backend_root = repo_root / "backend"
    dataset_path = _resolve_repo_path(repo_root, args.dataset_path)
    output_path = _resolve_repo_path(repo_root, args.output_file)
    input_markdown = repo_root / "backend" / "examples" / "cases" / "release_go_no_go_case" / "input" / "release_packet.md"
    build_dataset_path = backend_root / "scripts" / "build_release_packet_dataset.py"
    build_report_path = backend_root / "scripts" / "build_release_readiness_report.py"

    subprocess.run(
        [
            sys.executable,
            str(build_dataset_path),
            "--input-file",
            str(input_markdown),
            "--output-file",
            str(dataset_path),
            "--dataset-id",
            "release_go_no_go_async",
        ],
        cwd=str(repo_root),
        check=True,
    )

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

    temp_paths: list[Path] = []
    try:
        _wait_for_health(base_url, timeout_sec=args.startup_timeout_sec, process=process)

        task_id, status_payload, evidence_payload, events_summary, observability_summary = _run_async_retrieval(
            base_url=base_url,
            query=args.query,
            dataset_path=dataset_path,
        )

        status_file = _write_temp_json(status_payload, temp_paths)
        evidence_file = _write_temp_json(evidence_payload, temp_paths)
        events_summary_file = _write_temp_json(events_summary, temp_paths)

        subprocess.run(
            [
                sys.executable,
                str(build_report_path),
                "--task-id",
                task_id,
                "--query",
                args.query,
                "--status-file",
                str(status_file),
                "--evidence-file",
                str(evidence_file),
                "--events-summary-file",
                str(events_summary_file),
                "--output-file",
                str(output_path),
            ],
            cwd=str(repo_root),
            env=env,
            check=True,
        )

        details = status_payload.get("details", {})
        result = {
            "base_url": base_url,
            "dataset_path": str(dataset_path),
            "report": str(output_path),
            "retrieval_task_id": task_id,
            "retrieval_status": status_payload.get("status"),
            "execution_mode": details.get("execution_mode"),
            "async_provider": details.get("async_provider"),
            "correlation_id": details.get("correlation_id"),
            "dispatch_id": details.get("dispatch_id"),
            "queue_name": details.get("queue_name"),
            "queue_wait_ms": details.get("queue_wait_ms"),
            "retrieval_backend": details.get("retrieval_backend"),
            "quality_gate_status": details.get("quality_gate_status"),
            "evidence_blocks": len(evidence_payload.get("evidence_pack", {}).get("selected_blocks", [])),
            "top_sources": evidence_payload.get("evidence_pack", {}).get("selected_sources", [])[:5],
            "events_summary_total": events_summary.get("total_events"),
            "observability_total_tasks": observability_summary.get("total_tasks"),
            "observability_task_types": observability_summary.get("task_types", []),
        }
        print(json.dumps(result, ensure_ascii=False, indent=4))
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
        for path in temp_paths:
            path.unlink(missing_ok=True)


def _run_async_retrieval(*, base_url: str, query: str, dataset_path: Path) -> tuple[str, dict, dict, dict, dict]:
    start_status, start_payload = _request(
        "POST",
        f"{base_url}/api/v1/tasks/retrieval/start_async",
        payload={
            "query": query,
            "filters": {
                "project_id": "p1",
                "document_types": ["requirements", "methodology", "security", "operations", "governance"],
            },
            "task_context": {
                "requester": "demo-release-go-no-go-async",
                "case_dataset_path": str(dataset_path),
            },
        },
    )
    if start_status != 200:
        raise RuntimeError(f"Async retrieval failed: status={start_status}, payload={start_payload}")

    task_id = start_payload["task_id"]
    status_code, status_payload = _wait_for_task_completion(base_url, task_id, timeout_sec=90)
    evidence_code, evidence_payload = _request("GET", f"{base_url}/api/v1/tasks/{urllib.parse.quote(task_id)}/evidence")
    summary_code, summary_payload = _request(
        "GET",
        f"{base_url}/api/v1/tasks/events/summary?task_id={urllib.parse.quote(task_id)}&task_type=retrieval_pack",
    )
    observability_code, observability_payload = _request(
        "GET",
        f"{base_url}/api/v1/tasks/observability/summary?task_type=retrieval_pack",
    )
    if status_code != 200:
        raise RuntimeError(f"Retrieval status failed: status={status_code}, payload={status_payload}")
    if evidence_code != 200:
        raise RuntimeError(f"Retrieval evidence failed: status={evidence_code}, payload={evidence_payload}")
    if summary_code != 200:
        raise RuntimeError(f"Retrieval events summary failed: status={summary_code}, payload={summary_payload}")
    if observability_code != 200:
        raise RuntimeError(f"Retrieval observability summary failed: status={observability_code}, payload={observability_payload}")
    return task_id, status_payload, evidence_payload, summary_payload, observability_payload


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

    raise TimeoutError(f"Async retrieval task {task_id} не завершился вовремя. last={last_payload}")


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


def _resolve_repo_path(repo_root: Path, value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else repo_root / path


def _write_temp_json(payload: dict, paths: list[Path]) -> Path:
    handle = tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".json", delete=False)
    with handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
    path = Path(handle.name)
    paths.append(path)
    return path


if __name__ == "__main__":
    main()
