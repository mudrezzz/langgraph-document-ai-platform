# ADR-0034: Binary demo documents для Knowledge Factory acceptance

Дата: 2026-04-23

Статус: Accepted

## Контекст

ADR-0031 добавил parser boundary для `.docx` и `.pdf`, но основной release go/no-go multifile demo фактически содержал только `.md/.txt/.json`. Из-за этого ручной acceptance прогон не подтверждал поддержку binary document formats, хотя framework уже имел соответствующие adapters.

## Решение

1. Расширить `release_go_no_go_multifile_case/input` двумя входными документами:
   - `05_release_notes.docx`;
   - `06_audit_summary.pdf`.
2. Добавить генератор `backend/scripts/build_binary_demo_documents.py` и shell/PowerShell wrappers.
3. Добавить флаг `--build-binary-demo-docs` в canonical indexing/retrieval smoke scripts.
4. Обновить manual PostgreSQL runbook так, чтобы ручной acceptance прогон проверял `.md/.txt/.json/.docx/.pdf`.

## Последствия

- Demo теперь реально валидирует все форматы текущего parser boundary.
- Smoke Knowledge Indexing ожидает 6 canonical documents и file types `docx/json/md/pdf/txt`.
- PDF fixture может давать quality flag `low_text_density`; это ожидаемое поведение MVP parser quality gates.
- Binary fixtures остаются небольшими и версионируются вместе с demo, а generator нужен для восстановления/перезаписи fixture files.
