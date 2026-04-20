#!/usr/bin/env bash
set -euo pipefail

HOST_NAME="127.0.0.1"
PORT="8040"

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
OUTPUT_FILE="${BACKEND_ROOT}/examples/cases/release_go_no_go_case/output/authoring_traceability_result.json"

mkdir -p "$(dirname "${OUTPUT_FILE}")"

echo "[1/2] Smoke authoring API flow..."
SMOKE_OUTPUT="$(
    bash "${BACKEND_ROOT}/scripts/smoke_authoring_api.sh" \
      --host "${HOST_NAME}" \
      --port "${PORT}" \
      --query "Подготовь черновик release readiness и traceability для Payments v2" \
      --artifact-type "release_report" \
      --artifact-title "Release Authoring Traceability Demo" \
      --artifact-format "markdown" \
      --case-dataset-id "saa_release_readiness"
)"

echo "[2/2] Сохраняем demo-результат..."
printf '%s\n' "${SMOKE_OUTPUT}" >"${OUTPUT_FILE}"

echo "=== DEMO: Release Authoring Traceability Case ==="
echo "Output: ${OUTPUT_FILE}"
echo
echo "Краткий результат:"
echo "${SMOKE_OUTPUT}"
