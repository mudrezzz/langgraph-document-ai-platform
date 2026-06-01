# Manual Demo Checks

The document gives a short manual script that validates the operation of real binary parsers and the end-to-end demo path.

## 1. Preparing runtime

```bash
cd /root/langgraph-document-ai-platform
PATH="$(pwd)/.venv/bin:$PATH"

APP_RUNTIME_PROFILE=prod \
APP_DB_DSN=postgresql://app:app@127.0.0.1:55432/langgraph \
APP_DB_SCHEMA=app \
bash backend/scripts/postgres_up.sh

APP_RUNTIME_PROFILE=prod \
APP_DB_DSN=postgresql://app:app@127.0.0.1:55432/langgraph \
APP_DB_SCHEMA=app \
bash backend/scripts/postgres_migrate.sh
```

## 2. Checking real PDF/PPTX parsing in the Knowledge Indexing API

```bash
APP_RUNTIME_PROFILE=prod \
APP_DB_DSN=postgresql://app:app@127.0.0.1:55432/langgraph \
APP_DB_SCHEMA=app \
PATH="$(pwd)/.venv/bin:$PATH" \
bash backend/scripts/smoke_knowledge_indexing_api.sh --host 127.0.0.1 --port 8075 --build-binary-demo-docs \
  | tee /tmp/knowledge_indexing_api.json
```

Checks:

```bash
jq '.file_types' /tmp/knowledge_indexing_api.json
jq '[.parser_quality[] | select(.parser_family=="pptx")] | length' /tmp/knowledge_indexing_api.json
jq '.pdf_demo_proof' /tmp/knowledge_indexing_api.json
```

Expected:

- In `file_types` there are `"pptx"` and `"pdf"`.
- Counter `parser_family=="pptx"` is greater than 0.
- `pdf_demo_proof.found == true`.

## 3. Checking the cross-release go/no-go multifile demo

```bash
APP_RUNTIME_PROFILE=prod \
APP_DB_DSN=postgresql://app:app@127.0.0.1:55432/langgraph \
APP_DB_SCHEMA=app \
PATH="$(pwd)/.venv/bin:$PATH" \
bash backend/scripts/demo_release_go_no_go_multifile_case.sh --host 127.0.0.1 --port 8022
```

Check out the final artifact:

- `backend/examples/cases/release_go_no_go_multifile_case/output/release_readiness_report.md`

The report should include:

- `Canonical Quality Summary`;
- `Canonical Source Mapping`;
- evidence with PDF provenance/table metadata.

## 4. Stopping the environment

```bash
bash backend/scripts/postgres_down.sh --remove-volumes
```
