# Canonical E2E Walkthrough

Update date: 2026-04-30
Status: Active (P0 practical guide)

The goal of walkthrough is to go the full `documents -> indexing -> retrieval -> authoring -> HITL -> artifact` path through real APIs/scripts.

## 1. Preparing the environment

```bash
cd /root/langgraph-document-ai-platform
PATH="$(pwd)/.venv/bin:$PATH"
python3 -m venv .venv
pip install -e ./backend

bash backend/scripts/postgres_up.sh
bash backend/scripts/postgres_migrate.sh
```

Basic runtime for walkthrough:

```bash
export APP_RUNTIME_PROFILE=stage
export APP_DB_DSN=postgresql://app:app@127.0.0.1:55432/langgraph
export APP_DB_SCHEMA=app
export APP_ASYNC_PROVIDER=inline
```

## 2. Documents -> canonical indexing

Task: disassemble the demo corpus, apply the quality policy, save canonical documents + knowledge blocks.

```bash
APP_RUNTIME_PROFILE=stage \
APP_DB_DSN=postgresql://app:app@127.0.0.1:55432/langgraph \
APP_DB_SCHEMA=app \
PATH="$(pwd)/.venv/bin:$PATH" \
bash backend/scripts/smoke_knowledge_indexing_api.sh --host 127.0.0.1 --port 8075 --build-binary-demo-docs
```

We check in the JSON output:

- `status=completed`
- `file_types` contains binary formats (`pdf`, `docx`, `xlsx`, `pptx`)
- `quality_gate_status` present

## 3. Indexing -> retrieval (canonical source)

Task: perform retrieval on top of canonical corpus and pgvector index.

```bash
APP_RUNTIME_PROFILE=stage \
APP_DB_DSN=postgresql://app:app@127.0.0.1:55432/langgraph \
APP_DB_SCHEMA=app \
PATH="$(pwd)/.venv/bin:$PATH" \
bash backend/scripts/smoke_canonical_retrieval.sh --build-binary-demo-docs
```

We check:

- `retrieval_backend=pgvector`
- `embeddings_indexed > 0`
- `selected_blocks` is not empty
- in details there are `quality_gate_status` and `unresolved_gaps`

## 4. Retrieval -> authoring artifact

Task: obtain the final authoring artifact with traceability.

```bash
APP_RUNTIME_PROFILE=stage \
APP_DB_DSN=postgresql://app:app@127.0.0.1:55432/langgraph \
APP_DB_SCHEMA=app \
PATH="$(pwd)/.venv/bin:$PATH" \
bash backend/scripts/smoke_authoring_api.sh --host 127.0.0.1 --port 8030 --workflow-mode multi_step
```

We check:

- `task_status=completed`
- endpoint `GET /api/v1/tasks/{task_id}/artifact` returns `artifact_id`, `content`, `traceability`
- `traceability` has `retrieval_task_id` and `source_refs`

## 5. Authoring -> HITL loop -> final artifact

Task: review/approve the contour with iteration `needs_changes -> approve`.

```bash
APP_RUNTIME_PROFILE=stage \
APP_DB_DSN=postgresql://app:app@127.0.0.1:55432/langgraph \
APP_DB_SCHEMA=app \
PATH="$(pwd)/.venv/bin:$PATH" \
bash backend/scripts/smoke_authoring_async_api.sh --host 127.0.0.1 --port 8050 --workflow-mode multi_step --hitl-required --hitl-decision-sequence needs_changes,approve
```

We check:

- the task goes through `waiting_human`
- reviewer actions are recorded in `GET /api/v1/hitl/actions`
- final `artifact` available after approve

## 6. End-to-end report proof

For a human-readable end-to-end artifact:

```bash
APP_RUNTIME_PROFILE=stage \
APP_DB_DSN=postgresql://app:app@127.0.0.1:55432/langgraph \
APP_DB_SCHEMA=app \
PATH="$(pwd)/.venv/bin:$PATH" \
bash backend/scripts/demo_release_go_no_go_multifile_case.sh --host 127.0.0.1 --port 8022
```

Result:

- `backend/examples/cases/release_go_no_go_multifile_case/output/release_readiness_report.md`
- sections `Canonical Quality Summary` and `Canonical Source Mapping`

## 7. Completion

```bash
bash backend/scripts/postgres_down.sh --remove-volumes
```
