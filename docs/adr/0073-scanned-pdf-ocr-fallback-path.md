# ADR-0073: Scanned PDF OCR fallback path

- Статус: Accepted
- Дата: 2026-04-27

## Контекст

После ADR-0072 parser quality read-model уже умеет диагностировать scanned PDF через `pdf_no_extractable_text` и `ocr_required`, но canonical ingestion все еще терял содержимое таких документов.

Для Increment 31 нужен минимальный production-compatible OCR slice:

- без отдельной ingestion архитектуры;
- с детерминированным demo/test path;
- с возможностью подключить real OCR runtime в production-like окружении.

## Решение

1. Добавить boundary `PdfOcrGateway` в `domain_docs.parsing.ocr`.
2. Реализовать два adapter path:
   - `SidecarPdfOcrGateway` для deterministic fixture/demo/test режима;
   - `OcrmypdfGateway` для optional real CLI path с fallback на sidecar.
3. `CanonicalDocumentParser` для PDF действует так:
   - сначала пытается обычный text extraction через PyMuPDF;
   - если текст не извлечен, ставит `pdf_no_extractable_text` и `ocr_required`;
   - затем пытается OCR recovery через configured gateway;
   - при успехе пишет `ocr_applied` и `ocr_provider:*`, а recovered text становится canonical content blocks;
   - при неуспехе пишет `ocr_not_available` или `ocr_text_not_recovered`.
4. Runtime wiring идет через existing `ApiContainer` и env:
   - `APP_OCR_ENABLED`;
   - `APP_OCR_PROVIDER=sidecar|ocrmypdf`;
   - `APP_OCR_LANGUAGE`, `APP_OCR_TIMEOUT_SEC`.
5. Demo расширяется scanned PDF fixture и sidecar OCR text, чтобы OCR path был виден в smoke/manual runbook.

## Последствия

Плюсы:

- canonical ingestion начинает обрабатывать scanned PDF, а не только диагностировать их;
- demo/test path стабилен и не зависит от локального Tesseract/OCRmyPDF;
- production-like runtime может включить real OCR без ломки parser contract.

Минусы:

- sidecar OCR путь является deterministic fixture, а не real OCR;
- OCR quality/confidence пока не моделируются отдельно от `quality_flags`/`parser_quality.issues`;
- rich layout/table extraction для OCR PDF остается следующим slice.
