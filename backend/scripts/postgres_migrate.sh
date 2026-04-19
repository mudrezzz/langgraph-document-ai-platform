#!/usr/bin/env bash
set -euo pipefail

BACKEND_ENV_FILE=".env"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --backend-env-file)
            BACKEND_ENV_FILE="$2"
            shift 2
            ;;
        *)
            echo "Неизвестный аргумент: $1" >&2
            exit 1
            ;;
    esac
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
ENV_PATH="${BACKEND_ROOT}/${BACKEND_ENV_FILE}"

if [[ ! -f "${ENV_PATH}" ]]; then
    echo "Файл окружения не найден: ${ENV_PATH}" >&2
    exit 1
fi

# Загружаем key=value из .env в текущий процесс.
set -a
# shellcheck disable=SC1090
source "${ENV_PATH}"
set +a

"${SCRIPT_DIR}/apply_migrations.sh"
