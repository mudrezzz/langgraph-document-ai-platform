# Manual Run: PostgreSQL + Smoke + Advanced Demo

Brief up-to-date instructions for the Linux server.

## 1. Preparing the environment

```bash
cd /root/langgraph-document-ai-platform
python3 -m venv .venv
source .venv/bin/activate
pip install -e ./backend
pip install uvicorn pytest
chmod +x backend/scripts/*.sh
```

What to see:

- commands complete without errors;
- the project has `./.venv` (smoke/demo now automatically prefers this python).
- backend editable install pulls up parser boundary dependencies, including `python-docx` and `PyMuPDF`.

If editable install still fails on package discovery, use fallback without editable mode:

```bash
pip install -r <(python - <<'PY'
import tomllib
from pathlib import Path

data = tomllib.loads(Path('backend/pyproject.toml').read_text())
for item in data['project']['dependencies']:
    print(item)
PY
)
pip install uvicorn pytest
export PYTHONPATH="$(pwd)/backend:$(pwd)/backend/packages"
```

Optional for MCP:

```bash
pip install fastmcp
```

## 2. Create `backend/.env`

```bash
cat > backend/.env <<'EOF'
APP_RUNTIME_PROFILE=prod
APP_DB_DSN=postgresql://app:app@127.0.0.1:55432/langgraph
APP_DB_SCHEMA=app
APP_VECTOR_DIM=1536
APP_LLM_ENABLED=false
APP_LLM_PROVIDER=openrouter
APP_LLM_STRICT=false
OPENROUTER_API_KEY=
OPENROUTER_MODEL=openai/gpt-4o-mini
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_TIMEOUT_SEC=60
TEI_BASE_URL=
TEI_EMBEDDING_URL=
TEI_RERANK_URL=
TEI_API_KEY=
TEI_TIMEOUT_SEC=30
TEI_FALLBACK_ENABLED=false
APP_ASYNC_PROVIDER=inline
APP_CELERY_BROKER_URL=redis://127.0.0.1:56379/0
APP_CELERY_RESULT_BACKEND=redis://127.0.0.1:56379/0
APP_CELERY_QUEUE=authoring
APP_CELERY_INDEXING_QUEUE=knowledge-indexing
APP_CELERY_RETRIEVAL_QUEUE=retrieval
APP_HITL_MAX_ITERATIONS=2
APP_HITL_WAIT_TIMEOUT_SEC=1800
APP_SLA_TASK_DURATION_MS=0
APP_SLA_QUEUE_WAIT_MS=0
APP_AUTH_ENABLED=false
APP_INDEXING_QUALITY_POLICY_NAME=default_indexing_quality_policy_v1
APP_INDEXING_QUALITY_BLOCKING_FLAGS=empty_document,no_content_blocks,pdf_no_extractable_text,ocr_text_not_recovered
APP_INDEXING_QUALITY_WARNING_ONLY_FLAGS=
APP_INDEXING_ALLOW_RECOVERED_OCR=true
APP_INDEXING_OCR_RECOVERY_BLOCKING_FLAG=pdf_no_extractable_text
APP_INDEXING_OCR_RECOVERY_SUCCESS_FLAG=ocr_applied
APP_INDEXING_QUALITY_FORM_CONFIDENCE_MIN_SCORE=0
APP_INDEXING_QUALITY_FORM_CONFIDENCE_LOW_BLOCKING=false
APP_INDEXING_QUALITY_OCR_CONFIDENCE_MIN_SCORE=0
APP_INDEXING_QUALITY_OCR_CONFIDENCE_LOW_BLOCKING=false
REDIS_PORT=56379

POSTGRES_DB=langgraph
POSTGRES_USER=app
POSTGRES_PASSWORD=app
POSTGRES_PORT=55432
EOF
```

What does it mean:

- `prod` profile disables in-memory fallback persistence;
- it is the real PostgreSQL circuit that is checked.
- `APP_AUTH_ENABLED=false` saves the existing smoke/demo path without the required actor headers; for manual RBAC checking, you can temporarily enable `true`.

### Optional: manual RBAC check sensitive API

If you want to make sure with your own hands that the RBAC boundary works:

1. In `backend/.env` set `APP_AUTH_ENABLED=true`.
2. Restart the smoke/server API.
3. Check template write endpoint without role and with role:

```bash
curl -i -X PUT "http://127.0.0.1:8010/api/v1/templates/rbac_demo" \
  -H 'Content-Type: application/json' \
  -d '{"version":"1","sections":[{"section_id":"overview","title":"Overview"}]}'

curl -i -X PUT "http://127.0.0.1:8010/api/v1/templates/rbac_demo" \
  -H 'Content-Type: application/json' \
  -H 'X-Actor-Id: alice' \
  -H 'X-Actor-Roles: template_admin' \
  -d '{"version":"1","sections":[{"section_id":"overview","title":"Overview"}]}'
```

What to see:

- the first request returns `401 Unauthorized`;
- the second request returns `200 OK` and template payload.

## 3. Upgrade PostgreSQL and apply migrations

```bash
bash backend/scripts/postgres_up.sh
PATH="$(pwd)/.venv/bin:$PATH" bash backend/scripts/postgres_migrate.sh
```

What to see:

- container `langgraph-db` in `healthy` state;
- migrations `0001`..`0009` were applied.

## 4. Basic smoke retrieval

```bash
APP_RUNTIME_PROFILE=prod \
APP_DB_DSN=postgresql://app:app@127.0.0.1:55432/langgraph \
APP_DB_SCHEMA=app \
PATH="$(pwd)/.venv/bin:$PATH" \
bash backend/scripts/smoke_retrieval_api.sh --host 127.0.0.1 --port 8010
```

What to see in JSON:

- `start_status=completed`, `task_status=completed`;
- `evidence_blocks >= 1`;
- `history_contains_task=true`;
- `events_has_running_to_completed=true`;
- `events_summary_has_running_to_completed=true`.

How to interpret:

- this is the minimum confirmation that retrieval + task history + task events + events summary work in the PostgreSQL circuit.

## 5. Manual audit of events by `task_id`

If you want to manually pass the API after smoke:

```bash
APP_RUNTIME_PROFILE=prod \
APP_DB_DSN=postgresql://app:app@127.0.0.1:55432/langgraph \
APP_DB_SCHEMA=app \
PATH="$(pwd)/.venv/bin:$PATH" \
bash backend/scripts/smoke_retrieval_api.sh --host 127.0.0.1 --port 8010 --keep-server
```

Further:

```bash
TASK_ID="<task_id_from_smoke_json>"
curl -sS --get "http://127.0.0.1:8010/api/v1/tasks/events" \
  --data-urlencode "limit=20" \
  --data-urlencode "task_id=$TASK_ID" \
  --data-urlencode "task_type=retrieval_pack"

curl -sS --get "http://127.0.0.1:8010/api/v1/tasks/events/summary" \
  --data-urlencode "task_id=$TASK_ID" \
  --data-urlencode "task_type=retrieval_pack"

curl -sS --get "http://127.0.0.1:8010/api/v1/tasks/observability/summary" \
  --data-urlencode "task_type=retrieval_pack"
```

What to see:

- in `events` there are transitions `null -> running` and `running -> completed`;
- in `summary.transitions` there is `running -> completed`.
- `summary.daily[]` and `summary.weekly[]` have at least one bucket with `total_events > 0`;
- the observability summary contains the fields `avg_selected_block_count`, `avg_confidence`, `tasks_with_unresolved_gaps`, `llm_tokens_total`.
- when SLA env thresholds (`APP_SLA_TASK_DURATION_MS`, `APP_SLA_QUEUE_WAIT_MS`) are enabled, `p50/p95` and breach counters (`duration_sla_breaches_total`, `queue_wait_sla_breaches_total`) are visible in observability.

## 6. Extended demo: single-file script

```bash
APP_RUNTIME_PROFILE=prod \
APP_DB_DSN=postgresql://app:app@127.0.0.1:55432/langgraph \
APP_DB_SCHEMA=app \
PATH="$(pwd)/.venv/bin:$PATH" \
bash backend/scripts/demo_release_go_no_go_case.sh --host 127.0.0.1 --port 8020
```

What the script does:

1. takes `input/release_packet.md`;
2. builds a JSON dataset;
3. runs retrieval via `task_context.case_dataset_path`;
4. generates the report `output/release_readiness_report.md`.

What to see:

- `evidence_blocks > 0`;
- at the end the paths to `dataset` and `report` are displayed;
- the report contains GO/NO-GO, blockers, pending approvals, evidence sources, task events summary.

## 7. Extended demo: multi-file script

```bash
APP_RUNTIME_PROFILE=prod \
APP_DB_DSN=postgresql://app:app@127.0.0.1:55432/langgraph \
APP_DB_SCHEMA=app \
PATH="$(pwd)/.venv/bin:$PATH" \
bash backend/scripts/demo_release_go_no_go_multifile_case.sh --host 127.0.0.1 --port 8022
```

What the script does:

1. guarantees the availability of `.docx/.pdf/.xlsx/.pptx` demo input files;
2. launches the Knowledge Indexing API for the `input/` directory (`.md`, `.txt`, `.json`, `.docx`, `.pdf`, `.xlsx`, `.pptx`);
3. takes `indexed_doc_ids` from indexing task details;
4. runs retrieval via `task_context.knowledge_source=canonical` and `canonical_doc_ids`;
5. generates the report `output/release_readiness_report.md`.

What to see:

- `indexing_status=completed`;
- `quality_gate_status=warning` for the current PDF fixture;
- `knowledge_source=canonical`;
- `retrieval_backend=pgvector`;
- `quality_gate_status=passed|warning`;
- `evidence_blocks > 0`;
- `top_sources` contains documents from several files, including `.docx`/`.pdf` when relevant;
- the report contains `Canonical Quality Summary`, `Retrieval Quality` and `Canonical Source Mapping`.

## 8. Ready / Not implemented in the demo circuit

Ready:

- file-based input (`markdown -> dataset -> retrieval task`);
- multi-file canonical input (`directory -> canonical indexing -> retrieval task`) via `canonical_doc_ids`;
- audit of statuses and summary API in the same run;
- multi-step authoring cycle (`research -> writer -> reviewer -> assembly`);
- HITL loop with iterations (`needs_changes -> rewrite -> re-review -> waiting_human(iteration+1)`);
- a meaningful final markdown report for manual review.

Not implemented yet:

- rich layout semantics extraction (forms/complex table layouts/reading-order hardening beyond current baseline);
- separate reviewer UI/dashboard for monitoring the queue of HITL solutions;
- separate production dashboard for task event units for periods.

## 9. (Optional) Retrieval MCP check

```bash
PATH="$(pwd)/.venv/bin:$PATH" bash backend/scripts/run_retrieval_mcp.sh
```

What to see:

- MCP service starts without import error;
- tools `build_evidence_pack`, `search_summaries`, `search_blocks`, `lookup_source` are available;
- the process remains running and listens to MCP runtime until `Ctrl+C`.

How to interpret:

- `build_evidence_pack` retains the same end-to-end retrieval task contract;
- `search_summaries` searches for indexed canonical section summaries via pgvector;
- `search_blocks` searches for indexed canonical content blocks via pgvector;
- `lookup_source` returns source/canonical mapping by `doc_id`/`block_id` or `block_ref`;
- for PDF blocks `lookup_source` now also returns page-level/layout provenance (`page_number`, `reading_order_index`, `layout_kind`, `layout_source`, `bbox`);
- indexed tools require a PostgreSQL/pgvector circuit with previously completed Knowledge Indexing.

## 9.1. Smoke Retrieval MCP indexed tools

```bash
APP_RUNTIME_PROFILE=prod \
APP_DB_DSN=postgresql://app:app@127.0.0.1:55432/langgraph \
APP_DB_SCHEMA=app \
PATH="$(pwd)/.venv/bin:$PATH" \
bash backend/scripts/smoke_retrieval_mcp.sh --build-binary-demo-docs
```

What to see in JSON:

- `tool_names` contains `build_evidence_pack`, `search_summaries`, `search_blocks`, `lookup_source`;
- `summary_candidates >= 1`;
- `block_candidates >= 1`;
- `lookup_found=true`;
- for DOCX approval matrix lookup can show `lookup_source_kind=table_row`, `lookup_table_title=Approval Matrix`, `lookup_row_index`;
- for PDF evidence lookup can show `lookup_source_kind=page_block|table_row`, `lookup_page_number`, `lookup_reading_order_index`, `lookup_layout_kind`, `lookup_layout_source`;
- `summary_backend=pgvector` and `block_backend=pgvector`;
- `build_status=completed`;
- `evidence_blocks >= 1`.

How to interpret:

- this confirms the direct MCP path on top of the indexed canonical corpus without manually launching the retrieval API;
- smoke uses the same production-compatible assembly: canonical indexing, vector store, retrieval service and source lookup.

## 10. Smoke Repository MCP (document tools)

```bash
APP_RUNTIME_PROFILE=prod \
APP_DB_DSN=postgresql://app:app@127.0.0.1:55432/langgraph \
APP_DB_SCHEMA=app \
PATH="$(pwd)/.venv/bin:$PATH" \
bash backend/scripts/smoke_repository_mcp.sh
```

What to see in JSON:

- `upserted_doc_ids` contains 2 values;
- `loaded_doc_id` and `loaded_title` are filled;
- `list_total_returned >= 1`;
- `list_contains_doc_1=true` and `list_contains_doc_2=true`.

How to interpret:

- this confirms that the repository circuit in the PostgreSQL profile supports `upsert/get/list` via the MCP service layer.

## 11. (Optional) Checking Repository MCP runtime

```bash
PATH="$(pwd)/.venv/bin:$PATH" bash backend/scripts/run_repository_mcp.sh
```

What to see:

- MCP service `repository-mcp` starts without import error;
- the process remains running and listens to MCP runtime until `Ctrl+C`.

## 12. Smoke Artifact Writer MCP (generated artifacts)

```bash
APP_RUNTIME_PROFILE=prod \
APP_DB_DSN=postgresql://app:app@127.0.0.1:55432/langgraph \
APP_DB_SCHEMA=app \
PATH="$(pwd)/.venv/bin:$PATH" \
bash backend/scripts/smoke_artifact_writer_mcp.sh
```

What to see in JSON:

- `written_artifact_ids` contains 2 values;
- `loaded_artifact_id` and `loaded_title` are filled;
- `list_total_returned >= 1`;
- `list_contains_artifact_1=true` and `list_contains_artifact_2=true`.

How to interpret:

- this confirms that the artifact writer circuit in the PostgreSQL profile supports `write/get/list` via the MCP service layer.

## 13. (Optional) Checking Artifact Writer MCP runtime

```bash
PATH="$(pwd)/.venv/bin:$PATH" bash backend/scripts/run_artifact_writer_mcp.sh
```

What to see:

- MCP service `artifact-writer-mcp` starts without import error;
- the process remains running and listens to MCP runtime until `Ctrl+C`.

## 13.1. Smoke Template Library MCP (reusable templates)

```bash
APP_RUNTIME_PROFILE=prod \
APP_DB_DSN=postgresql://app:app@127.0.0.1:55432/langgraph \
APP_DB_SCHEMA=app \
PATH="$(pwd)/.venv/bin:$PATH" \
bash backend/scripts/smoke_template_library_mcp.sh
```

What to see in JSON:

- `upserted_template_id` and `loaded_template_id` are filled;
- `published_status=published` and `loaded_status=published`;
- `deprecated_status=deprecated`;
- `loaded_section_id=overview`;
- `list_total_returned >= 1`;
- `deprecated_total_returned >= 1`;
- `list_contains_template=true`.

How to interpret:

- this confirms that the persisted template library is accessible through the MCP service boundary, and not only through the HTTP API or internal authoring wiring;
- `upsert_template` runs the payload through the existing `TemplateCompiler`, then saves the compiled `TemplateSpec`;
- `publish_template` translates the desired version into `published` and supports exclusive published invariant;
- `set_template_status` allows you to manually change another version to `deprecated`/`archived` with governance metadata;
- `get_template` and `list_templates(status=...)` read the same persisted template records that the authoring path uses.

## 13.2. (Optional) Check Template Library MCP runtime

```bash
PATH="$(pwd)/.venv/bin:$PATH" bash backend/scripts/run_template_library_mcp.sh
```

What to see:

- MCP service `template-library-mcp` starts without import error;
- tools `upsert_template`, `publish_template`, `set_template_status`, `get_template`, `list_templates` are available;
- the process remains running and listens to MCP runtime until `Ctrl+C`.

## 13.2.1. Smoke Review/Approval MCP (reviewer/HITL tools)

```bash
APP_RUNTIME_PROFILE=prod \
APP_DB_DSN=postgresql://app:app@127.0.0.1:55432/langgraph \
APP_DB_SCHEMA=app \
PATH="$(pwd)/.venv/bin:$PATH" \
bash backend/scripts/smoke_review_approval_mcp.sh
```

What to see in JSON:

- `tool_names` contains `get_hitl_status`, `list_hitl_actions`, `submit_hitl_review`, `get_hitl_observability_summary`;
- `start_status=waiting_human`;
- `hitl_status_before=waiting_human`;
- `can_submit_before=true`;
- `submit_status=completed|queued|waiting_human`;
- `actions_after >= 1`;
- `summary_total_actions >= 1`;
- `summary_reviewers` contains the passed reviewer.

How to interpret:

- this confirms that the reviewer/HITL manual boundary is accessible through the MCP service layer, and not only through the HTTP API;
- `submit_hitl_review` uses the same `AuthoringApplicationService.submit_hitl(...)` and the same async dispatcher plane as the HTTP submit path;
- `get_hitl_status`, `list_hitl_actions` and `get_hitl_observability_summary` read the existing HITL read-model without a separate parallel persistence branch.

## 13.2.2. (Optional) Review/Approval MCP runtime

```bash
PATH="$(pwd)/.venv/bin:$PATH" bash backend/scripts/run_review_approval_mcp.sh
```

What to see:

- MCP service `review-approval-mcp` starts without import error;
- tools `get_hitl_status`, `list_hitl_actions`, `submit_hitl_review`, `get_hitl_observability_summary` are available;
- the process remains running and listens to MCP runtime until `Ctrl+C`.

## 13.2.3. Smoke Configuration Library MCP (versioned config artifacts)

```bash
APP_RUNTIME_PROFILE=prod \
APP_DB_DSN=postgresql://app:app@127.0.0.1:55432/langgraph \
APP_DB_SCHEMA=app \
PATH="$(pwd)/.venv/bin:$PATH" \
bash backend/scripts/smoke_configuration_library_mcp.sh
```

What to see in JSON:

- `tool_names` contains `upsert_config`, `get_config`, `list_configs`, `find_similar_configs`, `compare_configs`;
- `loaded_config_id` and `loaded_version` are filled;
- `updated_version` shows the second persisted version;
- `list_total_returned >= 2` and `list_contains_config=true`;
- `similar_total_returned >= 1`;
- `top_similar_config_id` is filled;
- `compare_changed_keys` contains at least `retrieval.top_k` or `quality_gates.min_sources`.

How to interpret:

- this confirms that versioned configuration artifacts are available through the MCP service boundary, and not just as internal JSON payloads;
- `upsert_config/get_config/list_configs` work on top of the persisted `configuration_library` store;
- `find_similar_configs` allows you to find a similar config bundle using deterministic heuristics without a new runtime stack;
- `compare_configs` shows changed settings between versions or different config artifacts.

## 13.2.4. (Optional) Checking Configuration Library MCP runtime

```bash
PATH="$(pwd)/.venv/bin:$PATH" bash backend/scripts/run_configuration_library_mcp.sh
```

What to see:

- MCP service `configuration-library-mcp` starts without import error;
- tools `upsert_config`, `get_config`, `list_configs`, `find_similar_configs`, `compare_configs` are available;
- the process remains running and listens to MCP runtime until `Ctrl+C`.

## 13.3. Smoke Knowledge Indexing

This smoke checks the real input of the demo case:

- `backend/examples/cases/release_go_no_go_multifile_case/input/01_scope_and_decision.md`
- `backend/examples/cases/release_go_no_go_multifile_case/input/02_security_findings.md`
- `backend/examples/cases/release_go_no_go_multifile_case/input/03_ops_readiness.txt`
- `backend/examples/cases/release_go_no_go_multifile_case/input/04_approvals.json`
- `backend/examples/cases/release_go_no_go_multifile_case/input/05_release_notes.docx`
- `backend/examples/cases/release_go_no_go_multifile_case/input/06_audit_summary.pdf`
- `backend/examples/cases/release_go_no_go_multifile_case/input/07_scanned_signoff.pdf`
- `backend/examples/cases/release_go_no_go_multifile_case/input/08_release_tracker.xlsx`
- `backend/examples/cases/release_go_no_go_multifile_case/input/09_release_briefing.pptx`

If you need to explicitly rebuild `.docx/.pdf/.xlsx/.pptx` inputs:

```bash
PATH="$(pwd)/.venv/bin:$PATH" \
bash backend/scripts/build_binary_demo_documents.sh --overwrite
```

Regular smoke can be run with the `--build-binary-demo-docs` flag: then `.docx/.pdf/.xlsx/.pptx` will be created before indexing if they do not exist.

```bash
APP_RUNTIME_PROFILE=prod \
APP_DB_DSN=postgresql://app:app@127.0.0.1:55432/langgraph \
APP_DB_SCHEMA=app \
PATH="$(pwd)/.venv/bin:$PATH" \
bash backend/scripts/smoke_knowledge_indexing.sh --build-binary-demo-docs
```

What to see in JSON:

- `documents_total=9`;
- `indexed_doc_ids` also contains `07SCANNE-*` for OCR fixture;
- `content_blocks_total` about `40` or more when fixture changes;
- `stored_blocks_for_indexed_docs_total` about `40` or more;
- `stored_blocks_total` may be larger if there were previous indexing smokes in the same database;
- `embeddings_indexed` about `40` or more;
- `file_types` contains `docx`, `json`, `md`, `pdf`, `pptx`, `txt`, `xlsx`;
- `quality_flags` contains `07SCANNE-*:ocr_required` and `07SCANNE-*:ocr_applied` for scanned PDF fixture;
- `quality_flags` can also contain `*:pdf_tables_extracted` and `*:pdf_form_like_blocks_detected` for `06_audit_summary.pdf`;
- `quality_flags` can also contain `*:pdf_rotated_layout_detected` for PDF with rotated text blocks;
- `quality_flags` may contain `*:pdf_table_extraction_partial` if part of the table-like blocks in the PDF were not extracted;
- when threshold is enabled (`APP_INDEXING_QUALITY_FORM_CONFIDENCE_MIN_SCORE>0`) `quality_flags` may contain `*:pdf_form_confidence_low`;
- when threshold is enabled (`APP_INDEXING_QUALITY_OCR_CONFIDENCE_MIN_SCORE>0`) `quality_flags` may contain `*:ocr_confidence_low`;
- `ocr_recovered_doc_ids` contains OCR fixture `07SCANNE-*`.
- `parser_quality_summary.policy_name=default_indexing_quality_policy_v1`;
- `parser_quality_summary.accepted_documents_total=9`;
- `parser_quality_summary.rejected_documents_total=0`;
- for `07SCANNE-*` there should no longer be `ocr_not_available` in direct smoke with `APP_OCR_ENABLED=true` and `APP_OCR_PROVIDER=sidecar`;
- in `parser_quality` for DOCX you can see `tables_total >= 1`, and in canonical DOCX there are `table_row` blocks from the approval matrix.
- in `parser_quality` for XLSX you can see `parser_family=xlsx`, and workbook sheet rows are included in the canonical corpus as `table_row` blocks.
- in `parser_quality` for `06_audit_summary.pdf` you can see `tables_total >= 1`, and in canonical PDF `table_row` blocks from table-like and form-like layout appear.
- in `parser_quality` for `06_audit_summary.pdf` by issue `pdf_form_like_blocks_detected` key/value + confidence diagnostics are visible, including multi-line form values.
- in `quality_summary` aggregate counters `documents_with_pdf_table_partial` and `documents_with_pdf_form_like` are visible.
- `quality_summary` also contains `documents_with_pdf_form_confidence_low`; when the threshold is active, `form_confidence_min_score` and `pdf_form_confidence_by_doc` are also visible.
- `quality_summary` also contains `documents_with_ocr_confidence_low`; when the threshold is active, `ocr_confidence_min_score` and `ocr_confidence_by_doc` are also visible.
- `pdf_demo_proof.found=true` and for `06_audit_summary.pdf` `tables_total>0`, `has_pdf_tables_extracted=true`, `has_pdf_form_like_blocks_detected=true` are visible.

How to interpret:

- this confirms that Knowledge Factory builds canonical documents from text, markdown, JSON, DOCX, XLSX, regular PDF and scanned PDF via OCR fallback;
- DOCX approval matrix and checklist actually fall into the canonical retrieval corpus, and are not just marked with quality flags;
- canonical documents latest-read are saved in `app.canonical_documents`;
- historical canonical versions are saved in `app.canonical_document_versions`;
- derived content blocks latest-read are saved in `app.knowledge_blocks`;
- historically derived content blocks are saved in `app.knowledge_block_versions`;
- embedding vectors for the latest content blocks are written in `app.embeddings`.

## 13.4. Smoke Knowledge Indexing API Task Lifecycle

This smoke checks the same indexing path through the FastAPI task endpoint:

```bash
APP_RUNTIME_PROFILE=prod \
APP_DB_DSN=postgresql://app:app@127.0.0.1:55432/langgraph \
APP_DB_SCHEMA=app \
PATH="$(pwd)/.venv/bin:$PATH" \
bash backend/scripts/smoke_knowledge_indexing_api.sh --build-binary-demo-docs
bash backend/scripts/smoke_knowledge_indexing_api.sh --build-binary-demo-docs --document-version 2
```

What to see in JSON:

- `start_status=completed`;
- `task_status=completed`;
- `document_version` reflects the requested indexing version;
- `documents_total=9`;
- `file_types` contains `docx`, `json`, `md`, `pdf`, `pptx`, `txt`, `xlsx`;
- `stored_blocks_total` about `40` or more;
- `embeddings_indexed` about `40` or more;
- `quality_gate_status=passed|warning`;
- `quality_summary.policy_name=default_indexing_quality_policy_v1`;
- `quality_summary.rejected_documents_total=0` for the current demo input;
- `ocr_recovered_doc_ids` contains scanned PDF doc_id;
- `pdf_demo_proof.found=true` and `pdf_demo_proof.has_pdf_tables_extracted=true` confirm extraction on a real demo PDF.
- `events_summary_has_running_to_completed=true`.

How to interpret:

- this confirms that Knowledge Indexing works as a full-fledged task lifecycle operation;
- `app.tasks` contains the task `task_type=knowledge_indexing`;
- `app.task_events` contains the transition `running -> completed`;
- checkpoint payload contains canonical documents, indexed ids and quality summary.

## 13.3. Smoke Canonical Retrieval

```bash
APP_RUNTIME_PROFILE=prod \
APP_DB_DSN=postgresql://app:app@127.0.0.1:55432/langgraph \
APP_DB_SCHEMA=app \
PATH="$(pwd)/.venv/bin:$PATH" \
bash backend/scripts/smoke_canonical_retrieval.sh \
  --build-binary-demo-docs \
  --query "release notes audit summary security sign-off customer notification"
```

What to see in JSON:

- `indexed_doc_ids` contains the same 6 canonical documents;
- `stored_blocks_for_indexed_docs_total` about `37` or more;
- `stored_blocks_total` may be larger due to past indexing runs in the same database;
- `embeddings_indexed` around `37` or more;
- `knowledge_source=canonical`;
- `retrieval_backend=pgvector`;
- `quality_gate_status=passed|warning`;
- `evidence_blocks > 0` (there are usually dozens of blocks on the current fixture);
- `top_sources` contains `05RELEAS-*` and `06AUDITS-*` for this binary-focused request;
- `task_status=completed`.

How to interpret:

- this confirms the path `canonical documents -> knowledge_blocks -> retrieval evidence pack`.
- summary/detail retrieval goes through pgvector-backed canonical retrievers, and not through the old demo dataset loader;
- retrieval quality gates are visible in task details and `EvidencePack.unresolved_gaps`.

## 13.4. Manual API run of canonical retrieval after indexing

If you want to check not only the smoke script, but also try the API manually, first perform indexing smoke from section 13.1 and take the `indexed_doc_ids` JSON array from it. Then bring up the API:

```bash
APP_RUNTIME_PROFILE=prod \
APP_DB_DSN=postgresql://app:app@127.0.0.1:55432/langgraph \
APP_DB_SCHEMA=app \
PATH="$(pwd)/.venv/bin:$PATH" \
uvicorn apps.api.main:app --app-dir backend --host 127.0.0.1 --port 8070
```

In another terminal, send a retrieval task over the canonical source:

```bash
curl -sS -X POST "http://127.0.0.1:8070/api/v1/tasks/retrieval/start" \
  -H "Content-Type: application/json" \
  -d '{
"query": "what is blocking the release of payments v2 and what approvals are pending",
    "filters": {
      "project_id": "p1",
      "document_types": ["requirements", "methodology", "security", "operations", "governance"]
    },
    "task_context": {
      "requester": "manual-canonical-demo",
      "knowledge_source": "canonical",
      "canonical_doc_ids": [
        "01SCOPEA-9912",
        "02SECURI-8031",
        "03OPSREA-1824",
        "04APPROV-5796",
        "05RELEAS-3554",
        "06AUDITS-1436"
      ]
    }
  }'
```

Replace the `canonical_doc_ids` values ​​with the actual IDs from your indexing smoke if they are different. From the response, take the `task_id`, then:

```bash
TASK_ID="<task_id_from_start_json>"
curl -sS "http://127.0.0.1:8070/api/v1/tasks/$TASK_ID"
curl -sS "http://127.0.0.1:8070/api/v1/tasks/$TASK_ID/evidence"
```

What to see:

- status contains `knowledge_source=canonical`, `retrieval_backend=pgvector`, `status=completed`;
- evidence pack contains sources from various demo input files, including `05_release_notes.docx` and/or `06_audit_summary.pdf`, if they were included in the top evidence for the request.

## 14. Smoke Authoring API (retrieval -> artifact + traceability)

```bash
APP_RUNTIME_PROFILE=prod \
APP_DB_DSN=postgresql://app:app@127.0.0.1:55432/langgraph \
APP_DB_SCHEMA=app \
PATH="$(pwd)/.venv/bin:$PATH" \
bash backend/scripts/smoke_authoring_api.sh --host 127.0.0.1 --port 8030 --workflow-mode multi_step
```

What to see in JSON:

- `start_status=completed` and `task_status=completed`;
- `artifact_id` and `artifact_title` are filled in;
- with `--artifact-format json` the `format` field is returned as `json`, and `content` contains a structured JSON artifact;
- `draft_generation_mode` is usually `deterministic` (if LLM is not enabled);
- `workflow_mode=multi_step`;
- `steps_total=4` (research/writer/reviewer/assembly);
- `traceability_sections >= 3`;
- `review_status` is complete (`completed|needs_revision|skipped`);
- `traceability_sources >= 1`;
- `events_summary_has_running_to_completed=true`.

How to interpret:

- this confirms that the authoring API flow generates the final artifact and maintains the traceability link to retrieval sources.

Checking with a real LLM via OpenRouter:

```bash
set -a && source backend/.env && set +a
APP_LLM_ENABLED=true APP_LLM_PROVIDER=openrouter APP_LLM_STRICT=true \
PATH="$(pwd)/.venv/bin:$PATH" \
bash backend/scripts/smoke_authoring_api.sh --host 127.0.0.1 --port 8030 --workflow-mode multi_step --draft-strategy llm --require-llm
```

What to see in JSON for LLM mode:

- `draft_generation_mode=llm`;
- `draft_model_provider=openrouter` and `draft_model_name` are filled in.
- `steps_total=4` and `traceability_sections >= 3`.

## 15. Raise Redis + Celery worker (async loop)

```bash
bash backend/scripts/async_up.sh
```

What to see:

- `redis` and `celery-worker` services are in `running`/`healthy` state (`docker compose ... ps`).

## 16. Smoke Async Authoring API + HITL

```bash
set -a && source backend/.env && set +a
APP_ASYNC_PROVIDER=celery \
APP_CELERY_BROKER_URL=redis://127.0.0.1:56379/0 \
APP_CELERY_RESULT_BACKEND=redis://127.0.0.1:56379/0 \
APP_HITL_MAX_ITERATIONS=2 \
PATH="$(pwd)/.venv/bin:$PATH" \
bash backend/scripts/smoke_authoring_async_api.sh --host 127.0.0.1 --port 8050 --workflow-mode multi_step --hitl-required --hitl-decision-sequence needs_changes,approve
```

Note:

- if PostgreSQL is not published on `55432`, add `APP_WORKER_DB_DSN=postgresql://...@host.docker.internal:<port>/langgraph` before running `async_up.sh`.

What to see in JSON:

- `start_status=queued`;
- the first pause comes as `waiting_human`, and `GET /api/v1/tasks/{task_id}/hitl` returns `phase=outline_review`;
- in `outline.sections[]` planned sections and their `source_refs` are visible;
- after the first submit (`needs_changes`) the task again becomes `waiting_human` with `hitl_iteration=2`;
- after the second submit (`approve`) the task reaches `task_status=completed`;
- `steps_total >= 4`;
- `traceability_sections >= 3`;
- `hitl_submit_count=2`;
- `hitl_actions_total=2` (checking the new read-model endpoint `/api/v1/hitl/actions`).
- `hitl_summary_total_actions=2`, `hitl_summary_pending_actions=0` and in `hitl_summary_decisions` `needs_changes` and `approve` are visible (check `/api/v1/hitl/observability/summary`).

How to interpret:

- this confirms that async launch via Celery/Redis works, and the reviewer first sees the outline approval point before section authoring;
- the same iterative path is additionally fixed in the real Docker/Celery e2e test `backend/tests/e2e/test_fastapi_authoring_async_celery_e2e.py`.

## 17. Advanced demo: authoring async + HITL

```bash
set -a && source backend/.env && set +a
APP_ASYNC_PROVIDER=celery \
APP_CELERY_BROKER_URL=redis://127.0.0.1:56379/0 \
APP_CELERY_RESULT_BACKEND=redis://127.0.0.1:56379/0 \
APP_HITL_MAX_ITERATIONS=2 \
PATH="$(pwd)/.venv/bin:$PATH" \
bash backend/scripts/demo_release_authoring_async_hitl_case.sh --host 127.0.0.1 --port 8060 --hitl-decision-sequence needs_changes,approve
```

What the script does:

1. starts async authoring via `authoring/start_async`;
2. waits for `waiting_human`;
3. performs a sequence of reviewer decisions (`needs_changes -> approve`);
4. saves the result in `output/authoring_async_hitl_result.json`.

## 18. Async Retrieval via Celery

```bash
set -a && source backend/.env && set +a
APP_ASYNC_PROVIDER=celery \
APP_CELERY_BROKER_URL=redis://127.0.0.1:56379/0 \
APP_CELERY_RESULT_BACKEND=redis://127.0.0.1:56379/0 \
APP_CELERY_RETRIEVAL_QUEUE=retrieval \
PATH="$(pwd)/.venv/bin:$PATH" \
bash backend/scripts/smoke_retrieval_async_api.sh --host 127.0.0.1 --port 8076
```

What to see:

- `start_status=queued`, and the final `task_status=completed`;
- `execution_mode=async`;
- there are `dispatch_id`, `correlation_id`, `queue_name`, `queue_wait_ms`;
- `events_summary_has_queued_to_running=true`;
- `events_summary_has_running_to_completed=true`;
- `observability_total_tasks >= 1`;
- `evidence_blocks >= 1`.

How to interpret:

- this confirms that retrieval is now executed through the same queue/Celery execution plane as authoring/indexing;
- the same path is fixed in the Docker/Celery e2e test `backend/tests/e2e/test_fastapi_authoring_async_celery_e2e.py`.

## 19. Extended demo: async retrieval release go/no-go

```bash
set -a && source backend/.env && set +a
APP_ASYNC_PROVIDER=celery \
APP_CELERY_BROKER_URL=redis://127.0.0.1:56379/0 \
APP_CELERY_RESULT_BACKEND=redis://127.0.0.1:56379/0 \
APP_CELERY_RETRIEVAL_QUEUE=retrieval \
PATH="$(pwd)/.venv/bin:$PATH" \
bash backend/scripts/demo_release_go_no_go_async_case.sh --host 127.0.0.1 --port 8023
```

What the script does:

1. rebuilds the file-based dataset from `release_packet.md`;
2. starts retrieval via `retrieval/start_async`;
3. waits for completion;
4. collects the final markdown report `release_readiness_report_async.md`.

What to see:

- `retrieval_status=completed`;
- `execution_mode=async`;
- `dispatch_id`, `correlation_id`, `queue_name` are visible in stdout;
- `evidence_blocks > 0`;
- `backend/examples/cases/release_go_no_go_case/output/release_readiness_report_async.md` appears next to it, where there is execution metadata.

## 20. Async Knowledge Indexing via Celery

```bash
set -a && source backend/.env && set +a
APP_ASYNC_PROVIDER=celery \
APP_CELERY_BROKER_URL=redis://127.0.0.1:56379/0 \
APP_CELERY_RESULT_BACKEND=redis://127.0.0.1:56379/0 \
APP_CELERY_INDEXING_QUEUE=knowledge-indexing \
PATH="$(pwd)/.venv/bin:$PATH" \
python backend/scripts/smoke_knowledge_indexing_api.py --host 127.0.0.1 --port 8075 --build-binary-demo-docs
```

What to see:

- in the response `start_status=queued`, and the final `task_status=completed`;
- there are `dispatch_id`, `correlation_id`, `queue_name`, `queue_wait_ms`;
- `events_summary_has_running_to_completed=true`;
- `observability_total_tasks >= 1`;
- `documents_total=9`, `stored_blocks_total > 0`, `quality_gate_status=passed|warning`;
- `quality_summary.parser_families` contains at least `docx`, `json`, `markdown`, `pdf`, `text`;
- `parser_quality` contains diagnostics for each `doc_id`, including scanned PDF with `ocr_required` and `ocr_applied`;
- the worker processes the task from the `knowledge-indexing` queue, not just the `authoring` one.

## 21. Extended demo: authoring + traceability

```bash
APP_RUNTIME_PROFILE=prod \
APP_DB_DSN=postgresql://app:app@127.0.0.1:55432/langgraph \
APP_DB_SCHEMA=app \
PATH="$(pwd)/.venv/bin:$PATH" \
bash backend/scripts/demo_release_authoring_traceability_case.sh --host 127.0.0.1 --port 8040
```

What the script does:

1. starts authoring smoke flow through the new endpoint `authoring/start`;
2. receives the final task artifact and summary events;
3. saves the result in `output/authoring_traceability_result.json`.

## 22. Unified Release Gate Smoke (PASS/FAIL JSON)

```bash
APP_RUNTIME_PROFILE=prod \
APP_DB_DSN=postgresql://app:app@127.0.0.1:55432/langgraph \
APP_DB_SCHEMA=app \
PATH="$(pwd)/.venv/bin:$PATH" \
bash backend/scripts/smoke_release_gate.sh --host 127.0.0.1 --port 8088 --gate-profile stage
```

What to see:

- JSON contains `gate_status=pass|fail`;
- `checks[]` contains a matrix of checks (`code`, `name`, `passed`, `expected`, `actual`, `message`);
- `failed_checks[]` duplicates only failed checks;
- `artifacts` contains payloads:
  - `retrieval_events_summary`;
  - `observability_summary`;
  - `hitl_summary`;
  - task payloads indexing/retrieval/authoring.

Useful env knobs:

- `APP_RELEASE_GATE_MIN_EVENTS_TOTAL`;
- `APP_RELEASE_GATE_MIN_OBSERVABILITY_TOTAL_TASKS`;
- `APP_RELEASE_GATE_MAX_DURATION_SLA_BREACHES`;
- `APP_RELEASE_GATE_MAX_QUEUE_WAIT_SLA_BREACHES`;
- `APP_RELEASE_GATE_REQUIRE_LLM_TOKENS=1` (requires `--draft-strategy llm` and a working OpenRouter key).

Profiles policy:

- `--gate-profile dev` (soft baseline);
- `--gate-profile stage` (moderately strict);
- `--gate-profile prod` (strict baseline, zero SLA breaches by default).

## 23. Final Release Decision Gate (official verdict)

```bash
APP_RUNTIME_PROFILE=prod \
APP_DB_DSN=postgresql://app:app@127.0.0.1:55432/langgraph \
APP_DB_SCHEMA=app \
PATH="$(pwd)/.venv/bin:$PATH" \
bash backend/scripts/release_decision_gate.sh --host 127.0.0.1 --port 8090 --gate-profile stage
```

What to see:

- script ended with code `0`;
- created `backend/.release_gate/release_decision_*.json`;
- in JSON:
  - `status=pass`;
  - `decision_reason`;
- `failed_checks` (empty list for pass);
- `test_gate_summary.summary_line` with the pytest gate summary.

## 24. Completing and stopping services

If you ran `--keep-server`, stop the API:

```bash
kill "$(cat backend/.smoke_uvicorn_8010.pid)" && rm -f backend/.smoke_uvicorn_8010.pid
```

Stop PostgreSQL and delete volume:

```bash
bash backend/scripts/async_down.sh --remove-volumes
bash backend/scripts/postgres_down.sh --remove-volumes
```
