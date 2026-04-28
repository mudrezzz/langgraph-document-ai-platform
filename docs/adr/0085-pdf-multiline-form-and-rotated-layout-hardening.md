# ADR-0085: PDF multi-line form and rotated-layout hardening

- Статус: Accepted
- Дата: 2026-04-28

## Контекст

После ADR-0084 quality gate учитывает form-confidence, но extraction baseline для PDF все еще уязвим к двум частым production-кейсам:

1. form-like поля с multi-line значениями;
2. rotated text blocks (90/270°), которые могут участвовать в table/form evidence.

Без этого parser либо теряет часть значения поля, либо не дает явного сигнала, что extraction шел по rotated layout.

## Решение

1. Расширить form-like parser:
   - поддержать ключи с пробелами и дефисами;
   - поддержать multi-line continuation values;
   - сохранять normalized key/value пары в existing `form_like` tabular path.
2. Добавить rotated layout hint в PDF block metadata:
   - `rotated_text=true|false` на page blocks и table_row blocks;
   - detection через `Page.get_text("dict")` line direction (`dir`).
3. Добавить parser quality flag `pdf_rotated_layout_detected` и diagnostics metadata:
   - `rotated_table_candidates_total`;
   - `rotated_table_candidates_extracted`.
4. Обновить demo fixture `06_audit_summary.pdf`:
   - multi-line form value;
   - rotated form-like line для ручной проверки smoke/demo.

## Последствия

Плюсы:

- лучшее покрытие реальных form-like PDF кейсов без изменения публичных API;
- rotated-layout path становится наблюдаемым в parser diagnostics;
- demo/smoke подтверждают hardening в ручном режиме.

Минусы:

- rotated hint — это lightweight heuristic, а не полноценный layout/OCR pipeline;
- merged/complex rotated tables остаются следующим этапом hardening.
