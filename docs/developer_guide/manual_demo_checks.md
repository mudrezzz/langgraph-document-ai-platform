# Manual Demo Checks

Документ дает короткий ручной сценарий, который подтверждает работу реальных binary parsers и сквозного demo-пути.

## 1. Подготовка runtime

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

## 2. Проверка реального PDF/PPTX parsing в Knowledge Indexing API

```bash
APP_RUNTIME_PROFILE=prod \
APP_DB_DSN=postgresql://app:app@127.0.0.1:55432/langgraph \
APP_DB_SCHEMA=app \
PATH="$(pwd)/.venv/bin:$PATH" \
bash backend/scripts/smoke_knowledge_indexing_api.sh --host 127.0.0.1 --port 8075 --build-binary-demo-docs \
  | tee /tmp/knowledge_indexing_api.json
```

Проверки:

```bash
jq '.file_types' /tmp/knowledge_indexing_api.json
jq '[.parser_quality[] | select(.parser_family=="pptx")] | length' /tmp/knowledge_indexing_api.json
jq '.pdf_demo_proof' /tmp/knowledge_indexing_api.json
```

Ожидается:

- В `file_types` есть `"pptx"` и `"pdf"`.
- Счетчик `parser_family=="pptx"` больше 0.
- `pdf_demo_proof.found == true`.

## 3. Проверка сквозного release go/no-go multifile demo

```bash
APP_RUNTIME_PROFILE=prod \
APP_DB_DSN=postgresql://app:app@127.0.0.1:55432/langgraph \
APP_DB_SCHEMA=app \
PATH="$(pwd)/.venv/bin:$PATH" \
bash backend/scripts/demo_release_go_no_go_multifile_case.sh --host 127.0.0.1 --port 8022
```

Проверьте итоговый артефакт:

- `backend/examples/cases/release_go_no_go_multifile_case/output/release_readiness_report.md`

В отчете должны быть:

- `Canonical Quality Summary`;
- `Canonical Source Mapping`;
- evidence с PDF provenance/table metadata.

## 4. Остановка окружения

```bash
bash backend/scripts/postgres_down.sh --remove-volumes
```
