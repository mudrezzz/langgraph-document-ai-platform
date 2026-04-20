#!/usr/bin/env bash
set -euo pipefail

HOST_NAME="127.0.0.1"
PORT="8020"

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
        *)
            echo "Неизвестный аргумент: $1" >&2
            exit 1
            ;;
    esac
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
BACKEND_ROOT="${REPO_ROOT}/backend"
CASE_ROOT="${BACKEND_ROOT}/examples/cases/release_go_no_go_case"
INPUT_MARKDOWN="${CASE_ROOT}/input/release_packet.md"
DATASET_JSON="${CASE_ROOT}/output/release_packet_dataset.generated.json"
REPORT_MARKDOWN="${CASE_ROOT}/output/release_readiness_report.md"
PID_FILE="${BACKEND_ROOT}/.demo_release_go_no_go_uvicorn_${PORT}.pid"

SMOKE_PATH="${SCRIPT_DIR}/smoke_retrieval_api.sh"
BUILD_DATASET_PATH="${SCRIPT_DIR}/build_release_packet_dataset.py"
BUILD_REPORT_PATH="${SCRIPT_DIR}/build_release_readiness_report.py"

if [[ -x "${REPO_ROOT}/.venv/bin/python" ]]; then
    # Предпочитаем локальное venv-окружение проекта для стабильного demo-прогона.
    PYTHON_BIN="${REPO_ROOT}/.venv/bin/python"
elif command -v python >/dev/null 2>&1; then
    PYTHON_BIN="python"
elif command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="python3"
else
    echo "Не найден интерпретатор python/python3" >&2
    exit 1
fi

PREV_PYTHONPATH="${PYTHONPATH-}"
SMOKE_JSON_FILE="$(mktemp)"
STATUS_FILE="$(mktemp)"
EVIDENCE_FILE="$(mktemp)"
EVENTS_SUMMARY_FILE="$(mktemp)"

cleanup() {
    if [[ -f "${PID_FILE}" ]]; then
        pid="$(cat "${PID_FILE}" 2>/dev/null || true)"
        if [[ -n "${pid}" ]] && kill -0 "${pid}" 2>/dev/null; then
            kill "${pid}" 2>/dev/null || true
            wait "${pid}" 2>/dev/null || true
        fi
        rm -f "${PID_FILE}"
    fi

    rm -f "${SMOKE_JSON_FILE}" "${STATUS_FILE}" "${EVIDENCE_FILE}" "${EVENTS_SUMMARY_FILE}"
    if [[ -z "${PREV_PYTHONPATH}" ]]; then
        unset PYTHONPATH
    else
        export PYTHONPATH="${PREV_PYTHONPATH}"
    fi
}

trap cleanup EXIT

export PYTHONPATH="${BACKEND_ROOT}:${BACKEND_ROOT}/packages${PYTHONPATH:+:${PYTHONPATH}}"

echo "[1/4] Сборка retrieval dataset из markdown release packet..."
"${PYTHON_BIN}" "${BUILD_DATASET_PATH}" \
    --input-file "${INPUT_MARKDOWN}" \
    --output-file "${DATASET_JSON}" \
    --dataset-id "release_go_no_go"

echo "[2/4] Smoke прогон API с file-based dataset (сервер остается поднятым)..."
QUERY="Что блокирует релиз Payments v2 и какие approvals еще не закрыты?"
"${SMOKE_PATH}" \
    --host "${HOST_NAME}" \
    --port "${PORT}" \
    --query "${QUERY}" \
    --case-dataset-id "release_go_no_go" \
    --case-dataset-path "${DATASET_JSON}" \
    --keep-server \
    --server-pid-file "${PID_FILE}" >"${SMOKE_JSON_FILE}"

BASE_URL="$("${PYTHON_BIN}" -c 'import json,sys; print(json.load(open(sys.argv[1], encoding="utf-8"))["base_url"])' "${SMOKE_JSON_FILE}")"
TASK_ID="$("${PYTHON_BIN}" -c 'import json,sys; print(json.load(open(sys.argv[1], encoding="utf-8"))["task_id"])' "${SMOKE_JSON_FILE}")"

echo "[3/4] Сбор evidence и audit summary по задаче ${TASK_ID}..."
curl -fsS "${BASE_URL}/api/v1/tasks/${TASK_ID}" >"${STATUS_FILE}"
curl -fsS "${BASE_URL}/api/v1/tasks/${TASK_ID}/evidence" >"${EVIDENCE_FILE}"
curl -fsS "${BASE_URL}/api/v1/tasks/events/summary?task_id=${TASK_ID}&task_type=retrieval_pack" >"${EVENTS_SUMMARY_FILE}"

echo "[4/4] Генерация осмысленного release readiness отчета..."
"${PYTHON_BIN}" "${BUILD_REPORT_PATH}" \
    --task-id "${TASK_ID}" \
    --query "${QUERY}" \
    --status-file "${STATUS_FILE}" \
    --evidence-file "${EVIDENCE_FILE}" \
    --events-summary-file "${EVENTS_SUMMARY_FILE}" \
    --output-file "${REPORT_MARKDOWN}"

echo "=== DEMO: Release Go/No-Go Case ==="
echo "Input markdown: ${INPUT_MARKDOWN}"
echo "Dataset JSON: ${DATASET_JSON}"
echo "Task ID: ${TASK_ID}"
echo "Report: ${REPORT_MARKDOWN}"
echo ""
echo "Краткий smoke result:"
cat "${SMOKE_JSON_FILE}"
