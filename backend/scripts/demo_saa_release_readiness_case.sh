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

QUERY="Какие ключевые ограничения и approval точки нужно учесть перед релизом SAA?"

result_json="$("${SMOKE_PATH}" \
    --host "${HOST_NAME}" \
    --port "${PORT}" \
    --case-dataset-id "saa_release_readiness" \
    --query "${QUERY}")"

python - <<'PY' <<<"${result_json}"
import json
import sys

result = json.load(sys.stdin)

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
PY
