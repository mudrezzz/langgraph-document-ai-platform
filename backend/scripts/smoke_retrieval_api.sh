#!/usr/bin/env bash
set -euo pipefail

HOST_NAME="127.0.0.1"
PORT="8000"
STARTUP_TIMEOUT_SEC="30"
QUERY="evidence pack retrieval"
CASE_DATASET_ID="saa_release_readiness"
KEEP_SERVER="false"
SERVER_PID_FILE=""
STARTED_OK="false"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --host)
            HOST_NAME="$2"
            shift 2
            ;;
        --port)
            PORT="$2"
            shift 2
            ;;
        --startup-timeout-sec)
            STARTUP_TIMEOUT_SEC="$2"
            shift 2
            ;;
        --query)
            QUERY="$2"
            shift 2
            ;;
        --case-dataset-id)
            CASE_DATASET_ID="$2"
            shift 2
            ;;
        --keep-server)
            KEEP_SERVER="true"
            shift
            ;;
        --server-pid-file)
            SERVER_PID_FILE="$2"
            shift 2
            ;;
        *)
            echo "Неизвестный аргумент: $1" >&2
            exit 1
            ;;
    esac
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
BACKEND_ROOT="${REPO_ROOT}/backend"
BASE_URL="http://${HOST_NAME}:${PORT}"

if command -v python >/dev/null 2>&1; then
    PYTHON_BIN="python"
elif command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="python3"
else
    echo "Не найден интерпретатор python/python3" >&2
    exit 1
fi

if ss -ltn | awk -v suffix=":${PORT}" '$4 ~ suffix"$" {found=1} END {exit !found}'; then
    echo "Порт ${PORT} уже занят. Остановите существующий процесс или укажите другой --port." >&2
    exit 1
fi

PREV_PYTHONPATH="${PYTHONPATH-}"

if [[ "${KEEP_SERVER}" == "true" ]]; then
    SERVER_LOG="${BACKEND_ROOT}/.smoke_uvicorn_${PORT}.log"
    if [[ -z "${SERVER_PID_FILE}" ]]; then
        SERVER_PID_FILE="${BACKEND_ROOT}/.smoke_uvicorn_${PORT}.pid"
    fi
    : >"${SERVER_LOG}"
else
    SERVER_LOG="$(mktemp)"
fi

START_FILE="$(mktemp)"
STATUS_FILE="$(mktemp)"
EVIDENCE_FILE="$(mktemp)"
RESUME_FILE="$(mktemp)"
HISTORY_FILE="$(mktemp)"
EVENTS_FILE="$(mktemp)"
EVENTS_SUMMARY_FILE="$(mktemp)"

cleanup() {
    if [[ -n "${SERVER_PID:-}" ]] && kill -0 "${SERVER_PID}" 2>/dev/null; then
        if [[ "${KEEP_SERVER}" == "true" && "${STARTED_OK}" == "true" ]]; then
            # Оставляем сервер поднятым для ручной проверки API после smoke-прогона.
            printf '%s\n' "${SERVER_PID}" >"${SERVER_PID_FILE}"
            echo "Smoke: API сервер оставлен запущенным (pid=${SERVER_PID})." >&2
            echo "Smoke: stop command -> kill \$(cat \"${SERVER_PID_FILE}\") && rm -f \"${SERVER_PID_FILE}\"" >&2
            echo "Smoke: server log -> ${SERVER_LOG}" >&2
        else
            kill "${SERVER_PID}" 2>/dev/null || true
            wait "${SERVER_PID}" 2>/dev/null || true
        fi
    fi

    if [[ "${KEEP_SERVER}" != "true" ]]; then
        rm -f "${SERVER_LOG}"
    fi
    rm -f "${START_FILE}" "${STATUS_FILE}" "${EVIDENCE_FILE}" "${RESUME_FILE}" "${HISTORY_FILE}" "${EVENTS_FILE}" "${EVENTS_SUMMARY_FILE}"

    if [[ -z "${PREV_PYTHONPATH}" ]]; then
        unset PYTHONPATH
    else
        export PYTHONPATH="${PREV_PYTHONPATH}"
    fi
}

trap cleanup EXIT

export PYTHONPATH="${BACKEND_ROOT}:${BACKEND_ROOT}/packages${PYTHONPATH:+:${PYTHONPATH}}"

if [[ "${KEEP_SERVER}" == "true" ]]; then
    # В keep-mode запускаем через nohup, чтобы процесс не завершился после выхода скрипта.
    SERVER_PID="$(
        cd "${BACKEND_ROOT}"
        nohup "${PYTHON_BIN}" -m uvicorn apps.api.main:app --host "${HOST_NAME}" --port "${PORT}" >>"${SERVER_LOG}" 2>&1 &
        echo "$!"
    )"
else
    (
        cd "${BACKEND_ROOT}"
        exec "${PYTHON_BIN}" -m uvicorn apps.api.main:app --host "${HOST_NAME}" --port "${PORT}"
    ) >"${SERVER_LOG}" 2>&1 &
    SERVER_PID=$!
fi

deadline=$((SECONDS + STARTUP_TIMEOUT_SEC))
started="false"

while (( SECONDS < deadline )); do
    if ! kill -0 "${SERVER_PID}" 2>/dev/null; then
        echo "API сервер завершился до поднятия /health" >&2
        cat "${SERVER_LOG}" >&2
        exit 1
    fi

    if health_json="$(curl -fsS "${BASE_URL}/health" 2>/dev/null)"; then
        health_status="$("${PYTHON_BIN}" -c 'import json,sys; print(json.loads(sys.stdin.read()).get("status",""))' <<<"${health_json}")"
        if [[ "${health_status}" == "ok" ]]; then
            started="true"
            break
        fi
    fi

    sleep 0.3
done

if [[ "${started}" != "true" ]]; then
    echo "API сервер не поднялся за ${STARTUP_TIMEOUT_SEC} секунд" >&2
    cat "${SERVER_LOG}" >&2
    exit 1
fi
STARTED_OK="true"

start_payload="$(QUERY="${QUERY}" CASE_DATASET_ID="${CASE_DATASET_ID}" "${PYTHON_BIN}" - <<'PY'
import json
import os

payload = {
    "query": os.environ["QUERY"],
    "filters": {
        "project_id": "p1",
        "document_types": ["requirements", "methodology", "security", "operations", "governance"],
    },
    "task_context": {
        "requester": "smoke-script-linux",
        "case_dataset_id": os.environ["CASE_DATASET_ID"],
    },
}

print(json.dumps(payload, ensure_ascii=False))
PY
)"

curl -fsS \
    -X POST \
    -H "Content-Type: application/json; charset=utf-8" \
    --data "${start_payload}" \
    "${BASE_URL}/api/v1/tasks/retrieval/start" >"${START_FILE}"

task_id="$("${PYTHON_BIN}" -c 'import json,sys; print(json.load(sys.stdin)["task_id"])' <"${START_FILE}")"

curl -fsS "${BASE_URL}/api/v1/tasks/${task_id}" >"${STATUS_FILE}"
curl -fsS "${BASE_URL}/api/v1/tasks/${task_id}/evidence" >"${EVIDENCE_FILE}"

resume_payload='{"decision":"rerun","comment":"smoke rerun","metadata":{"source":"smoke-script-linux"}}'
curl -fsS \
    -X POST \
    -H "Content-Type: application/json; charset=utf-8" \
    --data "${resume_payload}" \
    "${BASE_URL}/api/v1/tasks/${task_id}/resume" >"${RESUME_FILE}"

curl -fsS "${BASE_URL}/api/v1/tasks?limit=5&status=completed&task_type=retrieval_pack" >"${HISTORY_FILE}"
curl -fsS "${BASE_URL}/api/v1/tasks/events?limit=10&task_id=${task_id}&task_type=retrieval_pack" >"${EVENTS_FILE}"
curl -fsS "${BASE_URL}/api/v1/tasks/events/summary?task_id=${task_id}&task_type=retrieval_pack" >"${EVENTS_SUMMARY_FILE}"

"${PYTHON_BIN}" - "${BASE_URL}" "${CASE_DATASET_ID}" "${QUERY}" "${task_id}" "${START_FILE}" "${STATUS_FILE}" "${EVIDENCE_FILE}" "${RESUME_FILE}" "${HISTORY_FILE}" "${EVENTS_FILE}" "${EVENTS_SUMMARY_FILE}" <<'PY'
import json
import sys

(
    base_url,
    dataset_id,
    query,
    task_id,
    start_file,
    status_file,
    evidence_file,
    resume_file,
    history_file,
    events_file,
    events_summary_file,
) = sys.argv[1:]

with open(start_file, encoding="utf-8") as f:
    start_response = json.load(f)
with open(status_file, encoding="utf-8") as f:
    status_response = json.load(f)
with open(evidence_file, encoding="utf-8") as f:
    evidence_response = json.load(f)
with open(resume_file, encoding="utf-8") as f:
    resume_response = json.load(f)
with open(history_file, encoding="utf-8") as f:
    history_response = json.load(f)
with open(events_file, encoding="utf-8") as f:
    events_response = json.load(f)
with open(events_summary_file, encoding="utf-8") as f:
    events_summary_response = json.load(f)

top_sources = evidence_response.get("evidence_pack", {}).get("selected_sources", [])[:3]
history_items = history_response.get("items", [])
history_ids = {item.get("task_id") for item in history_items}
event_items = events_response.get("items", [])
has_completed_transition = any(
    item.get("from_status") == "running" and item.get("to_status") == "completed"
    for item in event_items
)
summary_transitions = events_summary_response.get("transitions", [])
summary_has_completed_transition = any(
    item.get("from_status") == "running" and item.get("to_status") == "completed"
    for item in summary_transitions
)

result = {
    "base_url": base_url,
    "dataset_id": dataset_id,
    "query": query,
    "task_id": task_id,
    "start_status": start_response.get("status"),
    "task_status": status_response.get("status"),
    "evidence_blocks": len(evidence_response.get("evidence_pack", {}).get("selected_blocks", [])),
    "top_sources": top_sources,
    "resume_status": resume_response.get("status"),
    "resume_decision": resume_response.get("details", {}).get("resume_decision"),
    "history_returned": len(history_items),
    "history_contains_task": task_id in history_ids,
    "events_returned": len(event_items),
    "events_has_running_to_completed": has_completed_transition,
    "events_summary_total": events_summary_response.get("total_events"),
    "events_summary_unique_tasks": events_summary_response.get("unique_tasks"),
    "events_summary_has_running_to_completed": summary_has_completed_transition,
}

print(json.dumps(result, ensure_ascii=False, indent=4))
PY
