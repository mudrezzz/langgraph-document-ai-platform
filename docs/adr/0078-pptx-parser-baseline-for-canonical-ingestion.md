# ADR-0078: PPTX parser baseline for canonical ingestion

- Статус: Accepted
- Дата: 2026-04-28

## Контекст

После slices с DOCX/XLSX/PDF/OCR в Increment 31 в canonical ingestion оставался последний формат из целевого baseline первого production-контура — `.pptx`.

Без PPTX parser презентационные артефакты (release briefings, steering decks, risk reviews) выпадали из единого Knowledge Factory path и требовали ручного дублирования содержимого в `.md/.docx`.

## Решение

1. Добавить `.pptx` в `CanonicalDocumentParser.supported_extensions()`.
2. Реализовать parser path через `python-pptx`:
   - slides становятся structural sections;
   - title/body content сохраняются в canonical blocks (`slide_title`, `paragraph`, `bullet`);
   - speaker notes сохраняются как canonical `note` blocks.
3. Расширить parser diagnostics flags:
   - `pptx_slides_detected`;
   - `pptx_notes_detected`.
4. Расширить binary demo input новым fixture `09_release_briefing.pptx` через existing generator `build_binary_demo_documents.py`.
5. Не вводить отдельный presentation-specific retrieval/indexing stack — PPTX reuse-ит текущий canonical/indexing/vector path.

## Последствия

Плюсы:

- canonical ingestion покрывает еще один production-relevant enterprise формат;
- multi-file demo действительно проверяет presentation ingestion в ручном smoke path;
- `.pptx` content сразу попадает в retrieval corpus и traceability path.

Минусы:

- baseline parser пока не извлекает изображения/диаграммы/rich layout geometry;
- table-aware extraction для PPTX остается будущим enrichment slice;
- notes extraction зависит от заполненности speaker notes в исходной презентации.
