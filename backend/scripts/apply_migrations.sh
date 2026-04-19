#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

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
python ./scripts/apply_migrations.py
