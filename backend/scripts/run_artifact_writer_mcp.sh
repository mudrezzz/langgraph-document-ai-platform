#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
BACKEND_ROOT="${REPO_ROOT}/backend"

if [[ -x "${REPO_ROOT}/.venv/bin/python" ]]; then
    # Предпочитаем локальный python из репозитория.
    PYTHON_BIN="${REPO_ROOT}/.venv/bin/python"
elif command -v python >/dev/null 2>&1; then
    PYTHON_BIN="python"
elif command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="python3"
else
    echo "Не найден интерпретатор python/python3" >&2
    exit 1
fi

if ! "${PYTHON_BIN}" -c "import fastmcp" >/dev/null 2>&1; then
    echo "Для запуска Artifact Writer MCP установите fastmcp: pip install fastmcp" >&2
    exit 1
fi

export PYTHONPATH="${BACKEND_ROOT}:${BACKEND_ROOT}/packages${PYTHONPATH:+:${PYTHONPATH}}"

cd "${BACKEND_ROOT}"
exec "${PYTHON_BIN}" -m apps.mcp_artifact_writer.main
