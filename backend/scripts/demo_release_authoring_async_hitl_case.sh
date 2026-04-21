#!/usr/bin/env bash
set -euo pipefail

HOST_NAME="127.0.0.1"
PORT="8060"
HITL_DECISION="approve"
HITL_DECISION_SEQUENCE=""

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
        --hitl-decision)
            HITL_DECISION="$2"
            shift 2
            ;;
        --hitl-decision-sequence)
            HITL_DECISION_SEQUENCE="$2"
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
OUTPUT_FILE="${BACKEND_ROOT}/examples/cases/release_go_no_go_case/output/authoring_async_hitl_result.json"

mkdir -p "$(dirname "${OUTPUT_FILE}")"

echo "[1/2] Smoke async authoring + HITL flow..."
SMOKE_EXTRA_ARGS=()
if [[ -n "${HITL_DECISION_SEQUENCE}" ]]; then
    SMOKE_EXTRA_ARGS+=(--hitl-decision-sequence "${HITL_DECISION_SEQUENCE}")
fi
SMOKE_OUTPUT="$(
    bash "${BACKEND_ROOT}/scripts/smoke_authoring_async_api.sh" \
      --host "${HOST_NAME}" \
      --port "${PORT}" \
      --query "Подготовь async release readiness draft с HITL решением" \
      --artifact-type "release_report" \
      --artifact-title "Release Async HITL Demo" \
      --artifact-format "markdown" \
      --workflow-mode "multi_step" \
      --draft-strategy "deterministic" \
      --hitl-decision "${HITL_DECISION}" \
      "${SMOKE_EXTRA_ARGS[@]}" \
      --hitl-required
)"

echo "[2/2] Сохраняем demo-результат..."
printf '%s\n' "${SMOKE_OUTPUT}" >"${OUTPUT_FILE}"

echo "=== DEMO: Release Authoring Async + HITL Case ==="
echo "Output: ${OUTPUT_FILE}"
echo
echo "Краткий результат:"
echo "${SMOKE_OUTPUT}"
