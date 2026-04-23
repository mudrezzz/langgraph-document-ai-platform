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

from scripts.build_binary_demo_documents import build_binary_demo_documents

QUERY = "Что блокирует релиз Payments v2 и какие approvals еще не закрыты?"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Canonical release go/no-go multifile demo")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8022)
    parser.add_argument("--startup-timeout-sec", type=int, default=30)
    parser.add_argument("--query", default=QUERY)
    parser.add_argument(
        "--input-path",
        default="backend/examples/cases/release_go_no_go_multifile_case/input",
    )
    parser.add_argument(
        "--output-file",
        default="backend/examples/cases/release_go_no_go_multifile_case/output/release_readiness_report.md",
    )
    parser.add_argument("--build-binary-demo-docs", dest="build_binary_demo_docs", action="store_true", default=True)
    parser.add_argument("--no-build-binary-demo-docs", dest="build_binary_demo_docs", action="store_false")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    repo_root = Path(__file__).resolve().parents[2]
    backend_root = repo_root / "backend"
    input_path = _resolve_repo_path(repo_root, args.input_path)
    output_path = _resolve_repo_path(repo_root, args.output_file)

    if args.build_binary_demo_docs:
        input_dir = input_path.parent if input_path.is_file() else input_path
        build_binary_demo_documents(output_dir=input_dir)

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

        indexing_task_id, indexing_status = _run_indexing(base_url=base_url, input_path=input_path)
        indexed_doc_ids = indexing_status.get("details", {}).get("indexed_doc_ids", [])
        retrieval_task_id, retrieval_status, evidence_payload, events_summary = _run_retrieval(
            base_url=base_url,
            query=args.query,
            canonical_doc_ids=indexed_doc_ids,
        )

        status_file = _write_temp_json(retrieval_status, temp_paths)
        evidence_file = _write_temp_json(evidence_payload, temp_paths)
        events_summary_file = _write_temp_json(events_summary, temp_paths)
        indexing_status_file = _write_temp_json(indexing_status, temp_paths)

        build_report_path = backend_root / "scripts" / "build_release_readiness_report.py"
        subprocess.run(
            [
                sys.executable,
                str(build_report_path),
                "--task-id",
                retrieval_task_id,
                "--query",
                args.query,
                "--status-file",
                str(status_file),
                "--evidence-file",
                str(evidence_file),
                "--events-summary-file",
                str(events_summary_file),
                "--indexing-status-file",
                str(indexing_status_file),
                "--output-file",
                str(output_path),
            ],
            cwd=str(repo_root),
            env=env,
            check=True,
        )

        result = {
            "base_url": base_url,
            "input_path": str(input_path),
            "report": str(output_path),
            "indexing_task_id": indexing_task_id,
            "indexing_status": indexing_status.get("status"),
            "indexed_doc_ids": indexed_doc_ids,
            "quality_gate_status": indexing_status.get("details", {}).get("quality_gate_status"),
            "retrieval_task_id": retrieval_task_id,
            "retrieval_status": retrieval_status.get("status"),
            "knowledge_source": retrieval_status.get("details", {}).get("knowledge_source"),
            "retrieval_backend": retrieval_status.get("details", {}).get("retrieval_backend"),
            "evidence_blocks": len(evidence_payload.get("evidence_pack", {}).get("selected_blocks", [])),
            "top_sources": evidence_payload.get("evidence_pack", {}).get("selected_sources", [])[:5],
            "events_summary_total": events_summary.get("total_events"),
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


def _run_indexing(*, base_url: str, input_path: Path) -> tuple[str, dict]:
    start_status, start_payload = _request(
        "POST",
        f"{base_url}/api/v1/tasks/knowledge-indexing/start",
        payload={
            "source_paths": [str(input_path)],
            "task_context": {
                "requester": "demo-release-go-no-go-canonical",
                "knowledge_source": "canonical",
            },
        },
    )
    if start_status != 200:
        raise RuntimeError(f"Knowledge indexing failed: status={start_status}, payload={start_payload}")
    task_id = start_payload["task_id"]
    status_code, status_payload = _request("GET", f"{base_url}/api/v1/tasks/{urllib.parse.quote(task_id)}")
    if status_code != 200:
        raise RuntimeError(f"Knowledge indexing status failed: status={status_code}, payload={status_payload}")
    return task_id, status_payload


def _run_retrieval(*, base_url: str, query: str, canonical_doc_ids: list[str]) -> tuple[str, dict, dict, dict]:
    start_status, start_payload = _request(
        "POST",
        f"{base_url}/api/v1/tasks/retrieval/start",
        payload={
            "query": query,
            "filters": {
                "project_id": "p1",
                "document_types": ["requirements", "methodology", "security", "operations", "governance"],
            },
            "task_context": {
                "requester": "demo-release-go-no-go-canonical",
                "knowledge_source": "canonical",
                "canonical_doc_ids": canonical_doc_ids,
            },
        },
    )
    if start_status != 200:
        raise RuntimeError(f"Canonical retrieval failed: status={start_status}, payload={start_payload}")

    task_id = start_payload["task_id"]
    status_code, status_payload = _request("GET", f"{base_url}/api/v1/tasks/{urllib.parse.quote(task_id)}")
    evidence_code, evidence_payload = _request("GET", f"{base_url}/api/v1/tasks/{urllib.parse.quote(task_id)}/evidence")
    summary_code, summary_payload = _request(
        "GET",
        f"{base_url}/api/v1/tasks/events/summary?task_id={urllib.parse.quote(task_id)}&task_type=retrieval_pack",
    )
    if status_code != 200:
        raise RuntimeError(f"Retrieval status failed: status={status_code}, payload={status_payload}")
    if evidence_code != 200:
        raise RuntimeError(f"Retrieval evidence failed: status={evidence_code}, payload={evidence_payload}")
    if summary_code != 200:
        raise RuntimeError(f"Retrieval events summary failed: status={summary_code}, payload={summary_payload}")
    return task_id, status_payload, evidence_payload, summary_payload


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
