# ADR-0036: Canonical release go/no-go demo report

Дата: 2026-04-23

Статус: Accepted

## Контекст

После ADR-0035 Knowledge Indexing стал полноценной task lifecycle операцией, но человекочитаемый `release_readiness_report.md` в multi-file demo все еще строился вокруг старого `case_dataset_dir` retrieval path. Это оставляло demo artifact слабым acceptance сигналом для Knowledge Factory: в отчете не было видно canonical quality flags, source path mapping и факта, что retrieval использует canonical source.

## Решение

1. Перевести `demo_release_go_no_go_multifile_case.sh/.ps1` на canonical route:
   - `POST /api/v1/tasks/knowledge-indexing/start`;
   - `POST /api/v1/tasks/retrieval/start` с `knowledge_source=canonical`;
   - `canonical_doc_ids` из indexing task details.
2. Расширить `build_release_readiness_report.py`:
   - принимать indexing status payload;
   - показывать `Canonical Quality Summary`;
   - строить `Canonical Source Mapping` из evidence block metadata.
3. Сохранять прежний output artifact path:
   - `backend/examples/cases/release_go_no_go_multifile_case/output/release_readiness_report.md`.

## Последствия

- Основной multi-file demo теперь проверяет полный путь `documents -> canonical documents -> knowledge_blocks -> embeddings -> retrieval -> report`.
- Ручная проверка видит, какие `.md/.txt/.json/.docx/.pdf` файлы участвовали в evidence pack.
- Quality flags стали частью demo artifact, а не только JSON-smoke.
- Старый `case_dataset_dir` retrieval path остается как быстрый fallback в `smoke_retrieval_api.sh`, но не является основным multi-file demo.
