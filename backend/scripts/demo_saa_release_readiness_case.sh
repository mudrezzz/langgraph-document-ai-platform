#!/usr/bin/env bash
set -euo pipefail

HOST_NAME="127.0.0.1"
PORT="8010"

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
SMOKE_PATH="${SCRIPT_DIR}/smoke_retrieval_api.sh"

if command -v python >/dev/null 2>&1; then
    PYTHON_BIN="python"
elif command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="python3"
else
    echo "Не найден интерпретатор python/python3" >&2
    exit 1
fi

QUERY="Какие ключевые ограничения и approval точки нужно учесть перед релизом SAA?"

result_json="$("${SMOKE_PATH}" \
    --host "${HOST_NAME}" \
    --port "${PORT}" \
    --case-dataset-id "saa_release_readiness" \
    --query "${QUERY}")"

RESULT_JSON="${result_json}" "${PYTHON_BIN}" - <<'PY'
import json
import os

result = json.loads(os.environ["RESULT_JSON"])

print("=== DEMO: SAA Release Readiness Case ===")
print(f"Task ID: {result.get('task_id')}")
print(f"Status: {result.get('task_status')}")
print(f"Evidence blocks: {result.get('evidence_blocks')}")
print("Top sources:")
for src in result.get("top_sources", []):
    print(f"- doc_id={src.get('doc_id')}, version={src.get('version')}, block_id={src.get('block_id')}")
print(f"Resume status: {result.get('resume_status')}")
print(f"History returned: {result.get('history_returned')}")
print(f"History contains task: {result.get('history_contains_task')}")
print(f"Events returned: {result.get('events_returned')}")
print(f"Has running->completed event: {result.get('events_has_running_to_completed')}")
print(f"Events summary total: {result.get('events_summary_total')}")
print(f"Events summary unique tasks: {result.get('events_summary_unique_tasks')}")
print(f"Summary has running->completed: {result.get('events_summary_has_running_to_completed')}")
PY
