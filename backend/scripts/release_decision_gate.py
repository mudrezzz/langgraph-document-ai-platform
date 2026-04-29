from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Final release decision gate: smoke_release_gate + full pytest verdict"
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8090)
    parser.add_argument("--gate-profile", choices=["dev", "stage", "prod"], default="stage")
    parser.add_argument("--draft-strategy", choices=["auto", "deterministic", "llm"], default="deterministic")
    parser.add_argument("--require-llm-tokens", action="store_true")
    parser.add_argument("--build-binary-demo-docs", action="store_true")
    parser.add_argument("--skip-knowledge-indexing", action="store_true")
    parser.add_argument("--skip-pytest", action="store_true")
    parser.add_argument("--pytest-path", default="backend/tests")
    parser.add_argument("--pytest-extra-args", default="-rs")
    parser.add_argument("--output-json", default="")
    parser.add_argument("--output-md", default="")
    parser.add_argument("--run-docker-async-e2e", action="store_true", default=True)
    parser.add_argument("--run-external-llm-tests", action="store_true", default=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    repo_root = Path(__file__).resolve().parents[2]
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output_dir = repo_root / "backend" / ".release_gate"
    output_dir.mkdir(parents=True, exist_ok=True)

    output_json = Path(args.output_json).resolve() if args.output_json else output_dir / f"release_decision_{timestamp}.json"
    output_md = Path(args.output_md).resolve() if args.output_md else output_dir / f"release_decision_{timestamp}.md"

    smoke_result = run_smoke_release_gate(repo_root=repo_root, args=args)
    pytest_result: dict[str, Any] = {"status": "skipped", "exit_code": None, "summary_line": "pytest skipped by flag"}
    if not args.skip_pytest:
        pytest_result = run_full_pytest_gate(repo_root=repo_root, args=args)

    payload = build_release_decision_payload(
        repo_root=repo_root,
        gate_profile=args.gate_profile,
        smoke_result=smoke_result,
        pytest_result=pytest_result,
    )

    output_json.write_text(json.dumps(payload, ensure_ascii=False, indent=4) + "\n", encoding="utf-8")
    output_md.write_text(_build_markdown_summary(payload), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=4))

    if payload["status"] != "pass":
        raise SystemExit(1)


def run_smoke_release_gate(*, repo_root: Path, args: argparse.Namespace) -> dict[str, Any]:
    script = repo_root / "backend" / "scripts" / "smoke_release_gate.py"
    cmd = [
        sys.executable,
        str(script),
        "--host",
        str(args.host),
        "--port",
        str(args.port),
        "--gate-profile",
        str(args.gate_profile),
        "--draft-strategy",
        str(args.draft_strategy),
    ]
    if args.require_llm_tokens:
        cmd.append("--require-llm-tokens")
    if args.build_binary_demo_docs:
        cmd.append("--build-binary-demo-docs")
    if args.skip_knowledge_indexing:
        cmd.append("--skip-knowledge-indexing")

    env = os.environ.copy()
    backend_root = repo_root / "backend"
    env["PYTHONPATH"] = f"{backend_root}{os.pathsep}{backend_root / 'packages'}"
    proc = subprocess.run(
        cmd,
        cwd=str(repo_root),
        env=env,
        capture_output=True,
        text=True,
    )
    stdout = proc.stdout.strip()
    stderr = proc.stderr.strip()
    parsed = _try_parse_json(stdout)
    return {
        "status": "pass" if proc.returncode == 0 else "fail",
        "exit_code": proc.returncode,
        "stdout": stdout,
        "stderr": stderr,
        "payload": parsed,
    }


def run_full_pytest_gate(*, repo_root: Path, args: argparse.Namespace) -> dict[str, Any]:
    env = os.environ.copy()
    _hydrate_openrouter_env_from_dotenv(repo_root=repo_root, env=env)
    if args.run_docker_async_e2e:
        env["RUN_DOCKER_ASYNC_E2E"] = "1"
    if args.run_external_llm_tests:
        env["RUN_EXTERNAL_LLM_TESTS"] = "1"

    pytest_bin = repo_root / ".venv" / "bin" / "pytest"
    cmd = [str(pytest_bin) if pytest_bin.exists() else "pytest", args.pytest_path]
    if args.pytest_extra_args.strip():
        cmd.extend(args.pytest_extra_args.strip().split())

    proc = subprocess.run(
        cmd,
        cwd=str(repo_root),
        env=env,
        capture_output=True,
        text=True,
    )
    combined = f"{proc.stdout}\n{proc.stderr}"
    summary_line = _extract_pytest_summary_line(combined)
    return {
        "status": "pass" if proc.returncode == 0 else "fail",
        "exit_code": proc.returncode,
        "summary_line": summary_line,
        "stdout_tail": "\n".join(proc.stdout.strip().splitlines()[-30:]),
        "stderr_tail": "\n".join(proc.stderr.strip().splitlines()[-30:]),
    }


def build_release_decision_payload(
    *,
    repo_root: Path,
    gate_profile: str,
    smoke_result: dict[str, Any],
    pytest_result: dict[str, Any],
) -> dict[str, Any]:
    smoke_payload = smoke_result.get("payload") or {}
    smoke_failed_checks = smoke_payload.get("failed_checks") or []
    failed_check_codes = [str(item.get("code", "")) for item in smoke_failed_checks if item.get("code")]
    smoke_pass = smoke_result.get("status") == "pass"
    pytest_pass = pytest_result.get("status") in {"pass", "skipped"}
    status = "pass" if (smoke_pass and pytest_pass) else "fail"

    if status == "pass":
        decision_reason = "Smoke release gate and pytest gate passed."
    elif not smoke_pass and not pytest_pass:
        decision_reason = (
            f"Smoke release gate failed (codes={failed_check_codes or ['unknown']}) and pytest gate failed."
        )
    elif not smoke_pass:
        decision_reason = f"Smoke release gate failed (codes={failed_check_codes or ['unknown']})."
    else:
        decision_reason = "Pytest gate failed."

    return {
        "status": status,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "profile": gate_profile,
        "commit_sha": _git_value(repo_root, ["rev-parse", "HEAD"]),
        "branch": _git_value(repo_root, ["rev-parse", "--abbrev-ref", "HEAD"]),
        "decision_reason": decision_reason,
        "failed_checks": smoke_failed_checks,
        "smoke_release_gate": {
            "status": smoke_result.get("status"),
            "exit_code": smoke_result.get("exit_code"),
            "gate_status": smoke_payload.get("gate_status"),
            "checks_total": len(smoke_payload.get("checks") or []),
            "failed_checks_total": len(smoke_failed_checks),
        },
        "test_gate_summary": {
            "status": pytest_result.get("status"),
            "exit_code": pytest_result.get("exit_code"),
            "summary_line": pytest_result.get("summary_line"),
        },
        "debug": {
            "smoke_stdout_tail": "\n".join((smoke_result.get("stdout") or "").splitlines()[-30:]),
            "smoke_stderr_tail": "\n".join((smoke_result.get("stderr") or "").splitlines()[-30:]),
            "pytest_stdout_tail": pytest_result.get("stdout_tail"),
            "pytest_stderr_tail": pytest_result.get("stderr_tail"),
        },
    }


def _build_markdown_summary(payload: dict[str, Any]) -> str:
    lines = [
        "# Release Decision",
        "",
        f"- status: `{payload.get('status')}`",
        f"- profile: `{payload.get('profile')}`",
        f"- commit_sha: `{payload.get('commit_sha')}`",
        f"- branch: `{payload.get('branch')}`",
        f"- timestamp_utc: `{payload.get('timestamp_utc')}`",
        f"- reason: {payload.get('decision_reason')}",
        "",
        "## Smoke Gate",
        "",
        f"- status: `{payload.get('smoke_release_gate', {}).get('status')}`",
        f"- gate_status: `{payload.get('smoke_release_gate', {}).get('gate_status')}`",
        f"- failed_checks_total: `{payload.get('smoke_release_gate', {}).get('failed_checks_total')}`",
        "",
        "## Test Gate",
        "",
        f"- status: `{payload.get('test_gate_summary', {}).get('status')}`",
        f"- summary: `{payload.get('test_gate_summary', {}).get('summary_line')}`",
    ]
    failed_checks = payload.get("failed_checks") or []
    if failed_checks:
        lines.extend(["", "## Failed Checks", ""])
        for item in failed_checks:
            lines.append(
                f"- `{item.get('code', 'n/a')}` {item.get('name', 'unknown')}: {item.get('message', '')}"
            )
    return "\n".join(lines).strip() + "\n"


def _hydrate_openrouter_env_from_dotenv(*, repo_root: Path, env: dict[str, str]) -> None:
    dotenv = repo_root / "backend" / ".env"
    if not dotenv.exists():
        return
    mapping = {
        "OPENROUTER_API_KEY": None,
        "OPENROUTER_MODEL": None,
        "OPENROUTER_BASE_URL": None,
    }
    try:
        for line in dotenv.read_text(encoding="utf-8").splitlines():
            if "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            if key in mapping and not env.get(key, "").strip():
                env[key] = value.strip()
    except OSError:
        return


def _extract_pytest_summary_line(output: str) -> str:
    for line in reversed(output.splitlines()):
        if "passed" in line and "in " in line and "=" in line:
            return line.strip()
    return "pytest summary not found"


def _try_parse_json(raw: str) -> dict[str, Any] | None:
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass
    match = re.search(r"(\{.*\})\s*$", raw, flags=re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group(1))
    except json.JSONDecodeError:
        return None


def _git_value(repo_root: Path, args: list[str]) -> str:
    try:
        proc = subprocess.run(
            ["git", *args],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            check=True,
        )
        return proc.stdout.strip()
    except Exception:
        return "unknown"


if __name__ == "__main__":
    main()
