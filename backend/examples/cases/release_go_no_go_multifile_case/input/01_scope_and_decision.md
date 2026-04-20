# Payments v2 Release Scope

## Scope
- В релиз входит checkout с 3DS2 и новый antifraud pre-check.
- Миграции затрагивают таблицы `payment_intents` и `payment_attempts`.
- За рамками релиза: частичные возвраты и Apple Pay web.

## Release Decision
- Релизное окно: 2026-04-26 22:00 UTC.
- Статус решения: CONDITIONAL GO до закрытия security/ops пунктов.
- При незакрытых блокерах после 2026-04-25 18:00 UTC решение меняется на NO-GO.
