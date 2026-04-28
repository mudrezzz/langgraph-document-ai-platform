# ADR-0084: PDF form-confidence scoring and policy gate

- Статус: Accepted
- Дата: 2026-04-28

## Контекст

После ADR-0082 и ADR-0083 parser уже извлекает form-like блоки и считает coverage для table-like extraction, но quality gate не учитывал надежность извлеченных form key/value данных. В результате частично заполненные или слабо распознанные формы проходили indexing без отдельного сигнала качества.

## Решение

1. Добавить PDF form-quality метрики в parser diagnostics:
   - `key_value_pairs_total`;
   - `key_value_pairs_extracted`;
   - `field_fill_rate_percent`;
   - `form_confidence_score`.
2. Прокинуть метрики в `parser_quality.issues` для `pdf_form_like_blocks_detected`.
3. Расширить `KnowledgeIndexingQualityPolicy` порогом `form_confidence_min_score`:
   - при score ниже порога policy добавляет synthetic flag `pdf_form_confidence_low`;
   - режим `warning`/`blocking` настраивается env-параметром.
4. Расширить aggregate quality summary:
   - `documents_with_pdf_form_confidence_low`;
   - `form_confidence_min_score`;
   - `pdf_form_confidence_by_doc` (score/threshold/is_low/blocking).

## Последствия

Плюсы:

- form-like extraction становится измеримым не только по факту извлечения, но и по качеству заполнения;
- production gate может мягко предупреждать или fail-fast блокировать низкокачественные формы без изменения API;
- smoke/report path прозрачно показывает threshold и документы с low-confidence.

Минусы:

- confidence score остается эвристическим baseline (не ML confidence);
- для сложных multi-line/rotated forms понадобится следующий hardening slice.
