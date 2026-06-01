# ADR-0084: PDF form-confidence scoring and policy gate

- Status: Accepted
- Date: 2026-04-28

## Context

After ADR-0082 and ADR-0083, the parser already extracts form-like blocks and calculates coverage for table-like extraction, but the quality gate did not take into account the reliability of the extracted form key/value data. As a result, partially completed or poorly recognized forms were indexed without a separate quality signal.

## Solution

1. Add PDF form-quality metrics to parser diagnostics:
   - `key_value_pairs_total`;
   - `key_value_pairs_extracted`;
   - `field_fill_rate_percent`;
   - `form_confidence_score`.
2. Upload metrics to `parser_quality.issues` for `pdf_form_like_blocks_detected`.
3. Expand `KnowledgeIndexingQualityPolicy` with the `form_confidence_min_score` threshold:
- when the score is below the threshold, policy adds a synthetic flag `pdf_form_confidence_low`;
- `warning`/`blocking` mode is configured by the env parameter.
4. Expand aggregate quality summary:
   - `documents_with_pdf_form_confidence_low`;
   - `form_confidence_min_score`;
   - `pdf_form_confidence_by_doc` (score/threshold/is_low/blocking).

## Consequences

Pros:

- form-like extraction becomes measurable not only by the fact of extraction, but also by the quality of filling;
- production gate can gently warn or fail-fastly block low-quality forms without changing the API;
- smoke/report path transparently shows threshold and documents with low-confidence.

Cons:

- confidence score remains a heuristic baseline (not ML confidence);
- for complex multi-line/rotated forms you will need the following hardening slice.
