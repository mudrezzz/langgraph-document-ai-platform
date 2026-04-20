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

## Скрипты

- Linux: `backend/scripts/demo_release_go_no_go_multifile_case.sh`
- Windows: `backend/scripts/demo_release_go_no_go_multifile_case.ps1`
