# Release Packet: Payments v2 (2026-04-20)

## Scope
- Релиз включает новый checkout flow с 3DS2 и маршрутизацией через платежный шлюз Stripe.
- В релиз входят миграции таблиц `payment_intents` и `payment_attempts`.
- Из scope исключены частичные возвраты и поддержка Apple Pay в web.

## Release Decision
- Целевое окно релиза: 2026-04-24 22:00-23:30 UTC.
- Текущий статус решения: CONDITIONAL GO при условии закрытия security и ops блокеров.
- Если блокеры не закрыты до 2026-04-23 18:00 UTC, решение автоматически меняется на NO-GO.

## Key Risks
- Риск деградации p95 latency checkout выше 900ms в пиковые часы.
- Риск блокировки платежей при истечении сертификата mTLS между API и payment gateway.
- Риск некорректной дедупликации retry webhook и двойного списания.

## Security
- [x] Проведен SAST/DAST для backend API.
- [ ] Не закрыт high finding SEC-4821: отсутствует ограничение rate-limit на endpoint подтверждения платежа.
- [ ] Не завершен повторный pentest после исправления webhook signature validation.
- [x] Секреты для production хранятся в vault и не попадают в репозиторий.

## Ops Readiness
- [x] Добавлены алерты по error rate и latency checkout.
- [ ] Не завершен нагрузочный прогон на 1500 RPS с профилем вечернего пика.
- [ ] Нет подтвержденного rollback dry-run на staging за последние 7 дней.
- [x] Подготовлена коммуникация инцидентного канала на релизное окно.

## Approvals
- Product approval: APPROVED (owner: pm@company, 2026-04-19).
- QA sign-off: APPROVED (owner: qa-lead@company, 2026-04-20).
- Security approval: PENDING (owner: appsec@company).
- SRE approval: PENDING (owner: sre-oncall@company).
- Release manager approval: WAITING final decision.

## Rollback Plan
- Версия приложения откатывается на `payments-v1.42.3` через blue/green switch за 8 минут.
- Миграции откатываются скриптом `20260420_payments_v2_down.sql`.
- После rollback включается ручной контроль webhook очереди и reconciliation job.

## Monitoring
- Ключевые KPI: success_rate, p95 checkout latency, auth_decline_rate.
- Для GO требуется: success_rate >= 97.5%, p95 <= 900ms, auth_decline_rate <= 4.5%.
- On-call канал: `#payments-release-war-room`, мост: `ops-bridge-17`.
