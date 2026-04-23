# Release Go/No-Go Multi-File Case

Мини-кейс для проверки retrieval по директории из нескольких файлов.

## Входные документы

- `input/01_scope_and_decision.md`
- `input/02_security_findings.md`
- `input/03_ops_readiness.txt`
- `input/04_approvals.json`

## Что демонстрирует

1. `task_context.case_dataset_dir` в API `start`.
2. Multi-file ingestion (`.md/.txt/.json`) без ручной сборки dataset JSON.
3. Генерацию итогового отчета `output/release_readiness_report.md`.
4. Canonical document indexing smoke через Knowledge Factory MVP.
5. Запись derived content blocks в `knowledge_blocks` read-model.
6. Retrieval поверх canonical `knowledge_blocks`.

## Скрипты

- Linux: `backend/scripts/demo_release_go_no_go_multifile_case.sh`
- Windows: `backend/scripts/demo_release_go_no_go_multifile_case.ps1`
- Canonical indexing smoke Linux: `backend/scripts/smoke_knowledge_indexing.sh`
- Canonical indexing smoke Windows: `backend/scripts/smoke_knowledge_indexing.ps1`
- Canonical retrieval smoke Linux: `backend/scripts/smoke_canonical_retrieval.sh`
- Canonical retrieval smoke Windows: `backend/scripts/smoke_canonical_retrieval.ps1`
