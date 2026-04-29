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
from typing import Any

from scripts.build_binary_demo_documents import build_binary_demo_documents

GATE_PROFILES: dict[str, dict[str, Any]] = {
    "dev": {
        "min_events_total": 2,
        "min_observability_total_tasks": 2,
        "max_duration_sla_breaches": -1,
        "max_queue_wait_sla_breaches": -1,
        "require_llm_tokens": False,
    },
    "stage": {
        "min_events_total": 2,
        "min_observability_total_tasks": 3,
        "max_duration_sla_breaches": 5,
        "max_queue_wait_sla_breaches": 5,
        "require_llm_tokens": False,
    },
    "prod": {
        "min_events_total": 2,
        "min_observability_total_tasks": 3,
        "max_duration_sla_breaches": 0,
        "max_queue_wait_sla_breaches": 0,
        "require_llm_tokens": False,
    },
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Release gate smoke: retrieval + authoring HITL + observability verdict")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8088)
    parser.add_argument("--startup-timeout-sec", type=int, default=30)
    parser.add_argument("--query", default="Что блокирует релиз и какие approvals еще не закрыты?")
    parser.add_argument("--authoring-query", default="подготовь release readiness draft с traceability")
    parser.add_argument("--case-dataset-id", default="saa_release_readiness")
    parser.add_argument("--case-dataset-path", default="")
    parser.add_argument("--case-dataset-dir", default="")
    parser.add_argument(
        "--input-path",
        default="backend/examples/cases/release_go_no_go_multifile_case/input",
        help="Директория/файл для knowledge indexing шага (если не отключен).",
    )
    parser.add_argument("--skip-knowledge-indexing", action="store_true")
    parser.add_argument("--build-binary-demo-docs", action="store_true")
    parser.add_argument("--document-version", default="1")
    parser.add_argument("--draft-strategy", default="deterministic", choices=["auto", "deterministic", "llm"])
    parser.add_argument("--workflow-mode", default="multi_step", choices=["single_pass", "multi_step"])
    parser.add_argument("--hitl-decision-sequence", default="needs_changes,approve")
    parser.add_argument(
        "--gate-profile",
        choices=sorted(GATE_PROFILES.keys()),
        default=os.getenv("APP_RELEASE_GATE_PROFILE", "dev").strip().lower() or "dev",
    )
    parser.add_argument("--min-events-total", type=int, default=None)
    parser.add_argument(
        "--min-observability-total-tasks",
        type=int,
        default=None,
    )
    parser.add_argument(
        "--max-duration-sla-breaches",
        type=int,
        default=None,
        help="-1 отключает проверку.",
    )
    parser.add_argument(
        "--max-queue-wait-sla-breaches",
        type=int,
        default=None,
        help="-1 отключает проверку.",
    )
    parser.add_argument("--require-llm-tokens", dest="require_llm_tokens", action="store_true")
    parser.add_argument("--no-require-llm-tokens", dest="require_llm_tokens", action="store_false")
    parser.set_defaults(require_llm_tokens=None)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    gate_policy = resolve_gate_policy(args)
    repo_root = Path(__file__).resolve().parents[2]
    backend_root = repo_root / "backend"
    base_url = f"http://{args.host}:{args.port}"

    input_path = Path(args.input_path)
    if not input_path.is_absolute():
        input_path = (repo_root / input_path).resolve()
    if args.build_binary_demo_docs:
        build_binary_demo_documents(output_dir=input_path if input_path.is_dir() else input_path.parent)

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
        canonical_doc_ids: list[str] = []
        indexing_payload: dict[str, Any] = {}

        if not args.skip_knowledge_indexing:
            indexing_task = _run_knowledge_indexing(
                base_url=base_url,
                input_path=input_path,
                document_version=args.document_version,
            )
            indexing_payload = indexing_task
            canonical_doc_ids = indexing_task.get("indexed_doc_ids", [])

        retrieval_task_id = _run_retrieval(
            base_url=base_url,
            query=args.query,
            case_dataset_id=args.case_dataset_id,
            case_dataset_path=args.case_dataset_path,
            case_dataset_dir=args.case_dataset_dir,
            canonical_doc_ids=canonical_doc_ids,
        )
        retrieval_events_summary = _get(
            base_url,
            f"/api/v1/tasks/events/summary?task_id={urllib.parse.quote(retrieval_task_id)}&task_type=retrieval_pack",
        )

        authoring_payload = _run_authoring_with_hitl(
            base_url=base_url,
            query=args.authoring_query,
            draft_strategy=args.draft_strategy,
            workflow_mode=args.workflow_mode,
            hitl_decision_sequence=args.hitl_decision_sequence,
            case_dataset_id=args.case_dataset_id,
            case_dataset_path=args.case_dataset_path,
            case_dataset_dir=args.case_dataset_dir,
            canonical_doc_ids=canonical_doc_ids,
        )
        hitl_summary = _get(
            base_url,
            f"/api/v1/hitl/observability/summary?task_id={urllib.parse.quote(authoring_payload['task_id'])}",
        )
        observability = _get(base_url, "/api/v1/tasks/observability/summary")

        checks = evaluate_release_gate(
            retrieval_events_summary=retrieval_events_summary,
            observability=observability,
            hitl_summary=hitl_summary,
            authoring_status=authoring_payload["status_payload"],
            require_llm_tokens=bool(gate_policy["require_llm_tokens"]),
            min_events_total=int(gate_policy["min_events_total"]),
            min_observability_total_tasks=int(gate_policy["min_observability_total_tasks"]),
            max_duration_sla_breaches=int(gate_policy["max_duration_sla_breaches"]),
            max_queue_wait_sla_breaches=int(gate_policy["max_queue_wait_sla_breaches"]),
        )
        gate_status = "pass" if all(item["passed"] for item in checks) else "fail"
        failed_checks = [item for item in checks if not item["passed"]]
        payload = {
            "gate_status": gate_status,
            "gate_profile": args.gate_profile,
            "gate_policy": gate_policy,
            "checks": checks,
            "failed_checks": failed_checks,
            "artifacts": {
                "base_url": base_url,
                "knowledge_indexing": indexing_payload,
                "retrieval_task_id": retrieval_task_id,
                "retrieval_events_summary": retrieval_events_summary,
                "authoring": authoring_payload,
                "hitl_summary": hitl_summary,
                "observability_summary": observability,
            },
        }
        print(json.dumps(payload, ensure_ascii=False, indent=4))
        if gate_status != "pass":
            raise SystemExit(1)
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()


def evaluate_release_gate(
    *,
    retrieval_events_summary: dict[str, Any],
    observability: dict[str, Any],
    hitl_summary: dict[str, Any],
    authoring_status: dict[str, Any],
    require_llm_tokens: bool,
    min_events_total: int,
    min_observability_total_tasks: int,
    max_duration_sla_breaches: int,
    max_queue_wait_sla_breaches: int,
) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    events_total = _as_non_negative_int(retrieval_events_summary.get("total_events"))
    checks.append(
        _check(
            code="RG001",
            name="retrieval_events_total",
            passed=events_total >= max(1, min_events_total),
            expected=f">= {max(1, min_events_total)}",
            actual=events_total,
        )
    )

    has_running_to_completed = any(
        item.get("from_status") == "running" and item.get("to_status") == "completed"
        for item in (retrieval_events_summary.get("transitions") or [])
    )
    checks.append(
        _check(
            code="RG002",
            name="retrieval_transition_running_to_completed",
            passed=has_running_to_completed,
            expected=True,
            actual=has_running_to_completed,
        )
    )
    checks.append(
        _check(
            code="RG003",
            name="retrieval_events_daily_non_empty",
            passed=bool(retrieval_events_summary.get("daily")),
            expected=True,
            actual=bool(retrieval_events_summary.get("daily")),
        )
    )
    checks.append(
        _check(
            code="RG004",
            name="retrieval_events_weekly_non_empty",
            passed=bool(retrieval_events_summary.get("weekly")),
            expected=True,
            actual=bool(retrieval_events_summary.get("weekly")),
        )
    )

    total_tasks = _as_non_negative_int(observability.get("total_tasks"))
    checks.append(
        _check(
            code="RG005",
            name="observability_total_tasks",
            passed=total_tasks >= max(1, min_observability_total_tasks),
            expected=f">= {max(1, min_observability_total_tasks)}",
            actual=total_tasks,
        )
    )
    checks.append(
        _check(
            code="RG006",
            name="observability_daily_non_empty",
            passed=bool(observability.get("daily")),
            expected=True,
            actual=bool(observability.get("daily")),
        )
    )
    checks.append(
        _check(
            code="RG007",
            name="observability_weekly_non_empty",
            passed=bool(observability.get("weekly")),
            expected=True,
            actual=bool(observability.get("weekly")),
        )
    )

    duration_breaches = _as_non_negative_int(observability.get("duration_sla_breaches_total"))
    if max_duration_sla_breaches >= 0:
        checks.append(
            _check(
                code="RG008",
                name="duration_sla_breaches",
                passed=duration_breaches <= max_duration_sla_breaches,
                expected=f"<= {max_duration_sla_breaches}",
                actual=duration_breaches,
            )
        )

    queue_wait_breaches = _as_non_negative_int(observability.get("queue_wait_sla_breaches_total"))
    if max_queue_wait_sla_breaches >= 0:
        checks.append(
            _check(
                code="RG009",
                name="queue_wait_sla_breaches",
                passed=queue_wait_breaches <= max_queue_wait_sla_breaches,
                expected=f"<= {max_queue_wait_sla_breaches}",
                actual=queue_wait_breaches,
            )
        )

    hitl_total_actions = _as_non_negative_int(hitl_summary.get("total_actions"))
    checks.append(
        _check(
            code="RG010",
            name="hitl_actions_recorded",
            passed=hitl_total_actions >= 1,
            expected=">= 1",
            actual=hitl_total_actions,
        )
    )

    if require_llm_tokens:
        details = authoring_status.get("details") or {}
        llm_tokens_total = _as_non_negative_int(details.get("llm_tokens_total"))
        draft_mode = str(details.get("draft_generation_mode", ""))
        checks.append(
            _check(
                code="RG011",
                name="llm_tokens_total_non_zero",
                passed=llm_tokens_total > 0,
                expected="> 0",
                actual=llm_tokens_total,
            )
        )
        checks.append(
            _check(
                code="RG012",
                name="draft_generation_mode_llm",
                passed=draft_mode == "llm",
                expected="llm",
                actual=draft_mode,
            )
        )

    return checks


def _run_knowledge_indexing(
    *,
    base_url: str,
    input_path: Path,
    document_version: str,
) -> dict[str, Any]:
    start_payload = _post(
        base_url,
        "/api/v1/tasks/knowledge-indexing/start",
        payload={
            "source_paths": [str(input_path)],
            "document_version": document_version,
            "task_context": {"requester": "smoke-release-gate", "knowledge_source": "canonical"},
        },
    )
    task_id = str(start_payload["task_id"])
    status_payload = _wait_for_task_completion(base_url, task_id, timeout_sec=120)
    details = status_payload.get("details") or {}
    return {
        "task_id": task_id,
        "status": status_payload.get("status"),
        "documents_total": details.get("documents_total"),
        "indexed_doc_ids": details.get("indexed_doc_ids", []),
        "quality_gate_status": details.get("quality_gate_status"),
    }


def _run_retrieval(
    *,
    base_url: str,
    query: str,
    case_dataset_id: str,
    case_dataset_path: str,
    case_dataset_dir: str,
    canonical_doc_ids: list[str],
) -> str:
    task_context: dict[str, Any] = {"requester": "smoke-release-gate-retrieval"}
    if canonical_doc_ids:
        task_context["knowledge_source"] = "canonical"
        task_context["canonical_doc_ids"] = canonical_doc_ids
    else:
        task_context["case_dataset_id"] = case_dataset_id
    if case_dataset_path.strip():
        task_context["case_dataset_path"] = str(Path(case_dataset_path).resolve())
    if case_dataset_dir.strip():
        task_context["case_dataset_dir"] = str(Path(case_dataset_dir).resolve())

    start_payload = _post(
        base_url,
        "/api/v1/tasks/retrieval/start",
        payload={
            "query": query,
            "filters": {
                "project_id": "p1",
                "document_types": ["requirements", "methodology", "security", "operations", "governance"],
            },
            "task_context": task_context,
        },
    )
    task_id = str(start_payload["task_id"])
    _ = _wait_for_task_completion(base_url, task_id, timeout_sec=90)
    return task_id


def _run_authoring_with_hitl(
    *,
    base_url: str,
    query: str,
    draft_strategy: str,
    workflow_mode: str,
    hitl_decision_sequence: str,
    case_dataset_id: str,
    case_dataset_path: str,
    case_dataset_dir: str,
    canonical_doc_ids: list[str],
) -> dict[str, Any]:
    task_context: dict[str, Any] = {"requester": "smoke-release-gate-authoring"}
    if canonical_doc_ids:
        task_context["knowledge_source"] = "canonical"
        task_context["canonical_doc_ids"] = canonical_doc_ids
    else:
        task_context["case_dataset_id"] = case_dataset_id
    if case_dataset_path.strip():
        task_context["case_dataset_path"] = str(Path(case_dataset_path).resolve())
    if case_dataset_dir.strip():
        task_context["case_dataset_dir"] = str(Path(case_dataset_dir).resolve())

    start_payload = _post(
        base_url,
        "/api/v1/tasks/authoring/start",
        payload={
            "query": query,
            "filters": {"project_id": "p1"},
            "task_context": task_context,
            "artifact_type": "release_report",
            "artifact_title": "Release Gate Smoke Draft",
            "artifact_format": "markdown",
            "draft_strategy": draft_strategy,
            "workflow_mode": workflow_mode,
            "hitl_required": True,
        },
    )
    task_id = str(start_payload["task_id"])
    status_payload = _get(base_url, f"/api/v1/tasks/{urllib.parse.quote(task_id)}")
    decisions = [item.strip() for item in hitl_decision_sequence.split(",") if item.strip()]
    if not decisions:
        decisions = ["approve"]

    submits: list[dict[str, Any]] = []
    decision_index = 0
    while status_payload.get("status") == "waiting_human":
        if decision_index >= len(decisions):
            raise RuntimeError(
                "Release gate authoring task все еще waiting_human, но decision sequence завершился."
            )
        hitl_payload = _get(base_url, f"/api/v1/tasks/{urllib.parse.quote(task_id)}/hitl")
        iteration = _as_non_negative_int(hitl_payload.get("current_iteration")) or 1
        decision = decisions[decision_index]
        decision_index += 1
        submit_payload = _post(
            base_url,
            f"/api/v1/tasks/{urllib.parse.quote(task_id)}/hitl/submit",
            payload={
                "decision": decision,
                "comment": f"release gate reviewer decision: {decision}",
                "metadata": {"source": "smoke-release-gate"},
                "idempotency_key": f"release-gate-{task_id}-{iteration}-{decision_index}",
                "expected_iteration": iteration,
            },
        )
        submits.append(
            {
                "iteration": iteration,
                "decision": decision,
                "submit_status": submit_payload.get("status"),
            }
        )
        status_payload = _wait_for_task_status(
            base_url,
            task_id,
            expected={"waiting_human", "completed", "failed"},
            timeout_sec=90,
        )

    artifact_payload: dict[str, Any] | None = None
    if status_payload.get("status") == "completed":
        artifact_payload = _get(base_url, f"/api/v1/tasks/{urllib.parse.quote(task_id)}/artifact")
    return {
        "task_id": task_id,
        "start_status": start_payload.get("status"),
        "status_payload": status_payload,
        "hitl_submits": submits,
        "artifact_id": artifact_payload.get("artifact_id") if artifact_payload else None,
        "draft_generation_mode": (artifact_payload or {}).get("metadata", {}).get("draft_generation_mode"),
    }


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


def _wait_for_task_completion(base_url: str, task_id: str, timeout_sec: int) -> dict[str, Any]:
    payload = _wait_for_task_status(
        base_url,
        task_id,
        expected={"completed", "failed"},
        timeout_sec=timeout_sec,
    )
    return payload


def _wait_for_task_status(
    base_url: str,
    task_id: str,
    *,
    expected: set[str],
    timeout_sec: int,
) -> dict[str, Any]:
    deadline = time.time() + timeout_sec
    last_payload: dict[str, Any] = {}
    while time.time() < deadline:
        status_code, payload = _request("GET", f"{base_url}/api/v1/tasks/{urllib.parse.quote(task_id)}")
        if status_code == 200:
            last_payload = payload
            if str(payload.get("status", "")) in expected:
                return payload
        time.sleep(0.5)
    raise TimeoutError(f"Task {task_id} не достиг статуса {expected}. last={last_payload}")


def _post(base_url: str, path: str, *, payload: dict[str, Any]) -> dict[str, Any]:
    status, body = _request("POST", f"{base_url}{path}", payload=payload)
    if status != 200:
        raise RuntimeError(f"POST {path} failed: status={status}, payload={body}")
    return body


def _get(base_url: str, path: str) -> dict[str, Any]:
    status, body = _request("GET", f"{base_url}{path}")
    if status != 200:
        raise RuntimeError(f"GET {path} failed: status={status}, payload={body}")
    return body


def _request(method: str, url: str, payload: dict[str, Any] | None = None) -> tuple[int, dict[str, Any]]:
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


def _check(*, code: str, name: str, passed: bool, expected: Any, actual: Any) -> dict[str, Any]:
    message = "ok" if passed else f"{code}:{name} expected={expected} actual={actual}"
    return {
        "code": code,
        "name": name,
        "passed": bool(passed),
        "expected": expected,
        "actual": actual,
        "message": message,
    }


def resolve_gate_policy(args: argparse.Namespace) -> dict[str, Any]:
    profile_name = str(args.gate_profile).strip().lower()
    if profile_name not in GATE_PROFILES:
        raise ValueError(f"Unsupported gate profile: {profile_name}")

    policy = dict(GATE_PROFILES[profile_name])

    env_min_events_total = _env_int("APP_RELEASE_GATE_MIN_EVENTS_TOTAL", policy["min_events_total"])
    env_min_observability_total_tasks = _env_int(
        "APP_RELEASE_GATE_MIN_OBSERVABILITY_TOTAL_TASKS",
        policy["min_observability_total_tasks"],
    )
    env_max_duration_sla_breaches = _env_int(
        "APP_RELEASE_GATE_MAX_DURATION_SLA_BREACHES",
        policy["max_duration_sla_breaches"],
    )
    env_max_queue_wait_sla_breaches = _env_int(
        "APP_RELEASE_GATE_MAX_QUEUE_WAIT_SLA_BREACHES",
        policy["max_queue_wait_sla_breaches"],
    )
    env_require_llm_tokens = _env_bool("APP_RELEASE_GATE_REQUIRE_LLM_TOKENS", bool(policy["require_llm_tokens"]))

    policy["min_events_total"] = env_min_events_total
    policy["min_observability_total_tasks"] = env_min_observability_total_tasks
    policy["max_duration_sla_breaches"] = env_max_duration_sla_breaches
    policy["max_queue_wait_sla_breaches"] = env_max_queue_wait_sla_breaches
    policy["require_llm_tokens"] = env_require_llm_tokens

    if args.min_events_total is not None:
        policy["min_events_total"] = max(1, int(args.min_events_total))
    if args.min_observability_total_tasks is not None:
        policy["min_observability_total_tasks"] = max(1, int(args.min_observability_total_tasks))
    if args.max_duration_sla_breaches is not None:
        policy["max_duration_sla_breaches"] = int(args.max_duration_sla_breaches)
    if args.max_queue_wait_sla_breaches is not None:
        policy["max_queue_wait_sla_breaches"] = int(args.max_queue_wait_sla_breaches)
    if args.require_llm_tokens is not None:
        policy["require_llm_tokens"] = bool(args.require_llm_tokens)

    return policy


def _as_non_negative_int(raw: Any) -> int:
    if isinstance(raw, int):
        return max(0, raw)
    if isinstance(raw, float):
        return max(0, int(raw))
    return 0


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name, "").strip().lower()
    if not raw:
        return default
    return raw in {"1", "true", "yes", "on"}


if __name__ == "__main__":
    main()
