# ADR-0086: OCR confidence calibration and policy gate

- Status: Accepted
- Date: 2026-04-28

## Context

After ADR-0073 scanned PDF path already restores text via OCR fallback, and after ADR-0084 quality policy can block low-confidence form extraction. But OCR path still did not provide a separate assessment of the reliability of the reconstructed text: the document could be `ocr_applied`, but the actual OCR quality remained opaque.

## Solution

1. Add OCR confidence diagnostics to parser quality issue `ocr_applied`:
   - `ocr_blocks_total`;
   - `ocr_words_total`;
   - `ocr_weird_char_ratio_percent`;
- `ocr_confidence_score` (heuristic baseline 0..100).
2. Expand `KnowledgeIndexingQualityPolicy` OCR confidence threshold:
   - env `APP_INDEXING_QUALITY_OCR_CONFIDENCE_MIN_SCORE`;
- synthetic flag `ocr_confidence_low` when score is below threshold;
- env ​​`APP_INDEXING_QUALITY_OCR_CONFIDENCE_LOW_BLOCKING=true|false` for warning/blocking mode.
3. Expand aggregate quality summary:
   - `documents_with_ocr_confidence_low`;
   - `ocr_confidence_min_score`;
   - `ocr_confidence_by_doc`.

## Consequences

Pros:

- scanned PDF ingestion receives the observed signal of OCR quality, and not just the fact of recovery;
- production gate can fail-fast block potentially unreadable OCR documents;
- the solution is completely additive and does not break public API/MCP contracts.

Cons:

- confidence score is heuristic and requires subsequent calibration on the production corpus;
- does not replace a full-fledged OCR engine confidence from an external provider.
