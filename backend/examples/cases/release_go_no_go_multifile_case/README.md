# Release Go/No-Go Multi-File Case

Мини-кейс для проверки retrieval по директории из нескольких файлов.

## Входные документы

- `input/01_scope_and_decision.md`
- `input/02_security_findings.md`
- `input/03_ops_readiness.txt`
- `input/04_approvals.json`
- `input/05_release_notes.docx`
- `input/06_audit_summary.pdf`
- `input/07_scanned_signoff.pdf`
- `input/08_release_tracker.xlsx`
- `input/09_release_briefing.pptx`

## Что демонстрирует

1. Knowledge Indexing API task для директории `input/`.
2. Multi-file canonical ingestion (`.md/.txt/.json/.docx/.pdf/.xlsx/.pptx`) без ручной сборки dataset JSON.
3. Генерацию итогового отчета `output/release_readiness_report.md`.
4. Canonical document indexing smoke через Knowledge Factory MVP.
5. Запись derived content blocks в `knowledge_blocks` read-model.
6. Retrieval поверх canonical `knowledge_blocks`.
7. Итоговый markdown report с canonical quality summary и source mapping.
8. PDF table/form extraction path: `06_audit_summary.pdf` содержит table-like и form-like layout (включая multi-line form values и rotated text line) для проверки `table_row` provenance.
9. PDF form-confidence policy gate: можно включить threshold и проверить `pdf_form_confidence_low` в `quality_summary`.

## Скрипты

- Linux: `backend/scripts/demo_release_go_no_go_multifile_case.sh`
- Windows: `backend/scripts/demo_release_go_no_go_multifile_case.ps1`
- Canonical indexing smoke Linux: `backend/scripts/smoke_knowledge_indexing.sh`
- Canonical indexing smoke Windows: `backend/scripts/smoke_knowledge_indexing.ps1`
- Canonical indexing API task smoke Linux: `backend/scripts/smoke_knowledge_indexing_api.sh`
- Canonical indexing API task smoke Windows: `backend/scripts/smoke_knowledge_indexing_api.ps1`
- Canonical retrieval smoke Linux: `backend/scripts/smoke_canonical_retrieval.sh`
- Canonical retrieval smoke Windows: `backend/scripts/smoke_canonical_retrieval.ps1`
- Binary input generator Linux: `backend/scripts/build_binary_demo_documents.sh`
- Binary input generator Windows: `backend/scripts/build_binary_demo_documents.ps1`

Для пересборки `.docx/.pdf/.xlsx/.pptx` входов:

```bash
bash backend/scripts/build_binary_demo_documents.sh --overwrite
```

Smoke scripts также поддерживают флаг `--build-binary-demo-docs`, чтобы перед прогоном гарантировать наличие binary input files.

Основной demo-скрипт `demo_release_go_no_go_multifile_case.sh/.ps1` запускает canonical indexing API, затем retrieval с `knowledge_source=canonical` и `canonical_doc_ids`, после чего обновляет `output/release_readiness_report.md`.

`smoke_knowledge_indexing.sh` и `smoke_knowledge_indexing_api.sh` теперь дополнительно печатают `pdf_demo_proof` для `06_audit_summary.pdf`, чтобы явно подтвердить table/form extraction на реальном PDF fixture.

Пример ручной проверки form-confidence threshold (warning mode):

```bash
APP_INDEXING_QUALITY_FORM_CONFIDENCE_MIN_SCORE=90 \
APP_INDEXING_QUALITY_FORM_CONFIDENCE_LOW_BLOCKING=false \
bash backend/scripts/smoke_knowledge_indexing_api.sh --build-binary-demo-docs
```

Пример ручной проверки OCR-confidence threshold (warning mode):

```bash
APP_INDEXING_QUALITY_OCR_CONFIDENCE_MIN_SCORE=70 \
APP_INDEXING_QUALITY_OCR_CONFIDENCE_LOW_BLOCKING=false \
bash backend/scripts/smoke_knowledge_indexing_api.sh --build-binary-demo-docs
```
