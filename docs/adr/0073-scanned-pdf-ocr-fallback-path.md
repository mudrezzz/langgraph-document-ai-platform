# ADR-0073: Scanned PDF OCR fallback path

- Status: Accepted
- Date: 2026-04-27

## Context

After ADR-0072, the parser quality read-model is already able to diagnose scanned PDF via `pdf_no_extractable_text` and `ocr_required`, but canonical ingestion still lost the contents of such documents.

For Increment 31 you need a minimum production-compatible OCR slice:

- without separate ingestion architecture;
- with deterministic demo/test path;
- with the ability to connect real OCR runtime in a production-like environment.

## Solution

1. Add boundary `PdfOcrGateway` to `domain_docs.parsing.ocr`.
2. Implement two adapter paths:
- `SidecarPdfOcrGateway` for deterministic fixture/demo/test mode;
- `OcrmypdfGateway` for optional real CLI path with fallback to sidecar.
3. `CanonicalDocumentParser` for PDF works like this:
- first tries regular text extraction via PyMuPDF;
- if the text is not extracted, sets `pdf_no_extractable_text` and `ocr_required`;
- then tries OCR recovery via configured gateway;
- if successful, writes `ocr_applied` and `ocr_provider:*`, and the recovered text becomes canonical content blocks;
- if unsuccessful, writes `ocr_not_available` or `ocr_text_not_recovered`.
4. Runtime wiring goes through the existing `ApiContainer` and env:
   - `APP_OCR_ENABLED`;
   - `APP_OCR_PROVIDER=sidecar|ocrmypdf`;
   - `APP_OCR_LANGUAGE`, `APP_OCR_TIMEOUT_SEC`.
5. Demo is expanded with scanned PDF fixture and sidecar OCR text so that the OCR path is visible in the smoke/manual runbook.

## Consequences

Pros:

- canonical ingestion begins to process scanned PDFs, and not just diagnose them;
- demo/test path is stable and does not depend on local Tesseract/OCRmyPDF;
- production-like runtime can enable real OCR without breaking the parser contract.

Cons:

- sidecar OCR path is a deterministic fixture, not real OCR;
- OCR quality/confidence are not yet modeled separately from `quality_flags`/`parser_quality.issues`;
- rich layout/table extraction for OCR PDF remains the next slice.
