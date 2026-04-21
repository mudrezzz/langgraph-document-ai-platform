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


def _wait_for_task_status(base_url: str, task_id: str, expected: set[str], timeout_sec: int = 90) -> tuple[str, dict]:
    deadline = time.time() + timeout_sec
    last_payload: dict = {}
    while time.time() < deadline:
        code, payload = _request("GET", f"{base_url}/api/v1/tasks/{task_id}")
        if code == 200:
            status = str(payload.get("status", ""))
            last_payload = payload
            if status in expected:
                return status, payload
        time.sleep(0.5)
    raise TimeoutError(f"Не дождались статуса {expected} для task {task_id}. last={last_payload}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Smoke-проверка async authoring API flow")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8050)
    parser.add_argument("--startup-timeout-sec", type=int, default=30)
    parser.add_argument("--query", default="подготовь release readiness draft async + hitl")
    parser.add_argument("--artifact-type", default="release_report")
    parser.add_argument("--artifact-title", default="Smoke Async Authoring Draft")
    parser.add_argument("--artifact-format", default="markdown")
    parser.add_argument("--draft-strategy", default="deterministic", choices=["auto", "deterministic", "llm"])
    parser.add_argument("--workflow-mode", default="multi_step", choices=["single_pass", "multi_step"])
    parser.add_argument("--hitl-decision", default="approve", choices=["approve", "needs_changes", "reject"])
    parser.add_argument(
        "--hitl-decision-sequence",
        default="",
        help="CSV последовательность решений HITL (например: needs_changes,approve)",
    )
    parser.add_argument("--case-dataset-id", default="saa_release_readiness")
    parser.add_argument("--case-dataset-path", default="")
    parser.add_argument("--case-dataset-dir", default="")
    parser.add_argument("--hitl-required", action="store_true")
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
            "requester": "smoke-authoring-async-api",
            "case_dataset_id": args.case_dataset_id,
        }
        if args.case_dataset_path.strip():
            task_context["case_dataset_path"] = str(Path(args.case_dataset_path).resolve())
        if args.case_dataset_dir.strip():
            task_context["case_dataset_dir"] = str(Path(args.case_dataset_dir).resolve())

        start_status, start_payload = _request(
            "POST",
            f"{base_url}/api/v1/tasks/authoring/start_async",
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
                "workflow_mode": args.workflow_mode,
                "hitl_required": args.hitl_required,
            },
        )
        if start_status != 200:
            raise RuntimeError(f"Authoring async start failed: status={start_status}, payload={start_payload}")

        task_id = start_payload["task_id"]
        expected_terminal = {"completed", "failed"}
        if args.hitl_required:
            expected_terminal = {"waiting_human", "failed", "completed"}

        task_status, task_payload = _wait_for_task_status(base_url, task_id, expected=expected_terminal)

        sequence_raw = [item.strip() for item in args.hitl_decision_sequence.split(",") if item.strip()]
        if sequence_raw:
            invalid = [item for item in sequence_raw if item not in {"approve", "needs_changes", "reject"}]
            if invalid:
                raise RuntimeError(f"Некорректные HITL решения в sequence: {invalid}")
            hitl_decisions = sequence_raw
        else:
            hitl_decisions = [args.hitl_decision]

        hitl_after_submit: dict | None = None
        hitl_submits: list[dict] = []
        submit_index = 0
        while task_payload.get("status") == "waiting_human":
            if submit_index >= len(hitl_decisions):
                raise RuntimeError(
                    "Задача все еще waiting_human, но список HITL решений закончился. "
                    "Добавьте --hitl-decision-sequence."
                )

            hitl_code, hitl_payload = _request("GET", f"{base_url}/api/v1/tasks/{task_id}/hitl")
            if hitl_code != 200:
                raise RuntimeError(f"HITL status failed: code={hitl_code}, payload={hitl_payload}")
            iteration = int(hitl_payload.get("current_iteration", 1))
            decision = hitl_decisions[submit_index]
            submit_index += 1

            submit_code, submit_payload = _request(
                "POST",
                f"{base_url}/api/v1/tasks/{task_id}/hitl/submit",
                payload={
                    "decision": decision,
                    "comment": f"smoke async reviewer decision: {decision}",
                    "metadata": {"source": "smoke-authoring-async"},
                    "idempotency_key": f"smoke-hitl-{task_id}-{iteration}-{submit_index}",
                    "expected_iteration": iteration,
                },
            )
            if submit_code != 200:
                raise RuntimeError(f"HITL submit failed: code={submit_code}, payload={submit_payload}")
            hitl_after_submit = submit_payload
            hitl_submits.append(
                {
                    "iteration": iteration,
                    "decision": decision,
                    "submit_status": submit_payload.get("status"),
                }
            )
            _, task_payload = _wait_for_task_status(
                base_url,
                task_id,
                expected={"waiting_human", "completed", "failed"},
            )

        artifact_code, artifact_payload = _request("GET", f"{base_url}/api/v1/tasks/{task_id}/artifact")
        if task_payload.get("status") == "completed" and artifact_code != 200:
            raise RuntimeError(f"Task artifact failed: status={artifact_code}, payload={artifact_payload}")

        result = {
            "base_url": base_url,
            "task_id": task_id,
            "start_status": start_payload.get("status"),
            "task_status": task_payload.get("status"),
            "task_current_node": task_payload.get("current_node"),
            "hitl_required": args.hitl_required,
            "hitl_submit_status": hitl_after_submit.get("status") if hitl_after_submit else None,
            "hitl_submit_count": len(hitl_submits),
            "hitl_submits": hitl_submits,
            "artifact_id": artifact_payload.get("artifact_id") if artifact_code == 200 else None,
            "artifact_title": artifact_payload.get("title") if artifact_code == 200 else None,
            "workflow_mode": artifact_payload.get("metadata", {}).get("workflow_mode") if artifact_code == 200 else None,
            "steps_total": len(artifact_payload.get("metadata", {}).get("steps_summary", [])) if artifact_code == 200 else 0,
            "traceability_sections": len(artifact_payload.get("traceability", {}).get("sections", [])) if artifact_code == 200 else 0,
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
