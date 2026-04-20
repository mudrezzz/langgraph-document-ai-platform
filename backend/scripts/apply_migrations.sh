#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

if command -v python >/dev/null 2>&1; then
    PYTHON_BIN="python"
elif command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="python3"
else
    echo "Не найден интерпретатор python/python3" >&2
    exit 1
fi

if [[ -z "${APP_DB_DSN:-}" ]]; then
    echo "Переменная APP_DB_DSN не задана" >&2
    exit 1
fi

PREV_PYTHONPATH="${PYTHONPATH-}"
export PYTHONPATH="${BACKEND_ROOT}:${BACKEND_ROOT}/packages${PYTHONPATH:+:${PYTHONPATH}}"

cleanup() {
    if [[ -z "${PREV_PYTHONPATH}" ]]; then
        unset PYTHONPATH
    else
        export PYTHONPATH="${PREV_PYTHONPATH}"
    fi
}

trap cleanup EXIT

cd "${BACKEND_ROOT}"
"${PYTHON_BIN}" ./scripts/apply_migrations.py
