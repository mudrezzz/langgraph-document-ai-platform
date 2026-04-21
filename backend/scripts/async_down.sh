#!/usr/bin/env bash
set -euo pipefail

COMPOSE_FILE="docker-compose.async.yml"
PROJECT_NAME="langgraph-async"
REMOVE_VOLUMES="false"

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
        --remove-volumes)
            REMOVE_VOLUMES="true"
            shift 1
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

if ! command -v docker >/dev/null 2>&1; then
    echo "Docker не найден в PATH" >&2
    exit 1
fi

if [[ ! -f "${COMPOSE_PATH}" ]]; then
    echo "Файл compose не найден: ${COMPOSE_PATH}" >&2
    exit 1
fi

cmd=(docker compose -f "${COMPOSE_PATH}" --project-name "${PROJECT_NAME}" down)
if [[ "${REMOVE_VOLUMES}" == "true" ]]; then
    cmd+=(--volumes)
fi

(
    cd "${BACKEND_ROOT}"
    "${cmd[@]}"
)

echo "Redis + Celery worker контейнеры остановлены."
