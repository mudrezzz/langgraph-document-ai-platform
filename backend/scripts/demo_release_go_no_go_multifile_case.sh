#!/usr/bin/env bash
set -euo pipefail

HOST_NAME="127.0.0.1"
PORT="8022"
BUILD_BINARY_DEMO_DOCS="true"

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
        --no-build-binary-demo-docs)
            BUILD_BINARY_DEMO_DOCS="false"
            shift
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

if [[ -x "${REPO_ROOT}/.venv/bin/python" ]]; then
    PYTHON_BIN="${REPO_ROOT}/.venv/bin/python"
elif command -v python >/dev/null 2>&1; then
    PYTHON_BIN="python"
elif command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="python3"
else
    echo "Не найден интерпретатор python/python3" >&2
    exit 1
fi

export PYTHONPATH="${BACKEND_ROOT}:${BACKEND_ROOT}/packages${PYTHONPATH:+:${PYTHONPATH}}"

ARGS=(
    "${BACKEND_ROOT}/scripts/demo_release_go_no_go_multifile_case.py"
    --host "${HOST_NAME}"
    --port "${PORT}"
)
if [[ "${BUILD_BINARY_DEMO_DOCS}" == "true" ]]; then
    ARGS+=(--build-binary-demo-docs)
else
    ARGS+=(--no-build-binary-demo-docs)
fi

exec "${PYTHON_BIN}" "${ARGS[@]}"
