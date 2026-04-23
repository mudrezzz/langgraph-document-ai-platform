#!/usr/bin/env bash
set -euo pipefail

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

if ! "${PYTHON_BIN}" -c "import uvicorn" >/dev/null 2>&1; then
    echo "В выбранном интерпретаторе (${PYTHON_BIN}) не найден модуль uvicorn." >&2
    echo "Активируйте .venv или установите зависимости (например: pip install -e ./backend uvicorn)." >&2
    exit 1
fi

export PYTHONPATH="${BACKEND_ROOT}:${BACKEND_ROOT}/packages${PYTHONPATH:+:${PYTHONPATH}}"

cd "${REPO_ROOT}"
exec "${PYTHON_BIN}" "${BACKEND_ROOT}/scripts/smoke_knowledge_indexing_api.py" "$@"
