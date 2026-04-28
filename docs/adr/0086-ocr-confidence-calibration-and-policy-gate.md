# ADR-0086: OCR confidence calibration and policy gate

- Статус: Accepted
- Дата: 2026-04-28

## Контекст

После ADR-0073 scanned PDF path уже восстанавливает текст через OCR fallback, а после ADR-0084 quality policy умеет блокировать low-confidence form extraction. Но OCR path по-прежнему не давал отдельной оценки надежности восстановленного текста: документ мог быть `ocr_applied`, но фактическое качество OCR оставалось непрозрачным.

## Решение

1. Добавить OCR confidence diagnostics в parser quality issue `ocr_applied`:
   - `ocr_blocks_total`;
   - `ocr_words_total`;
   - `ocr_weird_char_ratio_percent`;
   - `ocr_confidence_score` (эвристический baseline 0..100).
2. Расширить `KnowledgeIndexingQualityPolicy` OCR confidence threshold:
   - env `APP_INDEXING_QUALITY_OCR_CONFIDENCE_MIN_SCORE`;
   - synthetic flag `ocr_confidence_low` при score ниже threshold;
   - env `APP_INDEXING_QUALITY_OCR_CONFIDENCE_LOW_BLOCKING=true|false` для warning/blocking режима.
3. Расширить aggregate quality summary:
   - `documents_with_ocr_confidence_low`;
   - `ocr_confidence_min_score`;
   - `ocr_confidence_by_doc`.

## Последствия

Плюсы:

- scanned PDF ingestion получает наблюдаемый signal качества OCR, а не только факт recovery;
- production gate может fail-fast блокировать потенциально нечитабельные OCR документы;
- решение полностью аддитивно и не ломает публичные API/MCP контракты.

Минусы:

- confidence score эвристический и требует последующей калибровки на production corpus;
- не заменяет полноценный OCR engine confidence от внешнего провайдера.
