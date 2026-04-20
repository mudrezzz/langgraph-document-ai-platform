#!/usr/bin/env bash
set -euo pipefail

COMPOSE_FILE="docker-compose.postgres.yml"
PROJECT_NAME="langgraph"
BACKEND_ENV_FILE=".env"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --compose-file)
            COMPOSE_FILE="$2"
            shift 2
            ;;
        --project-name)
            PROJECT_NAME="$2"
            shift 2
            ;;
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
COMPOSE_PATH="${BACKEND_ROOT}/${COMPOSE_FILE}"
ENV_PATH="${BACKEND_ROOT}/${BACKEND_ENV_FILE}"

if ! command -v docker >/dev/null 2>&1; then
    echo "Docker не найден в PATH" >&2
    exit 1
fi

if [[ ! -f "${COMPOSE_PATH}" ]]; then
    echo "Файл compose не найден: ${COMPOSE_PATH}" >&2
    exit 1
fi

cmd=(docker compose -f "${COMPOSE_PATH}" --project-name "${PROJECT_NAME}")
if [[ -f "${ENV_PATH}" ]]; then
    cmd+=(--env-file "${ENV_PATH}")
fi
cmd+=(up -d)

(
    cd "${BACKEND_ROOT}"
    "${cmd[@]}"
)

echo "PostgreSQL контейнер поднят."
echo "Проверьте статус: docker compose -f ${COMPOSE_PATH} --project-name ${PROJECT_NAME} ps"
