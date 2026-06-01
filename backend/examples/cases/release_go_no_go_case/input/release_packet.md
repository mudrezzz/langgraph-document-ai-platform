# Release Packet: Payments v2 (2026-04-20)

## Scope
- The release includes a new checkout flow with 3DS2 and routing through the Stripe payment gateway.
- The release includes migrations of tables `payment_intents` and `payment_attempts`.
- Partial refunds and support for Apple Pay on the web are excluded from scope.

## Release Decision
- Target release window: 2026-04-24 22:00-23:30 UTC.
- Current status of the solution: CONDITIONAL GO, subject to the closure of security and ops blockers.
- If blockers are not closed before 2026-04-23 18:00 UTC, the decision automatically changes to NO-GO.

## Key Risks
- Risk of degradation of p95 latency checkout above 900ms during peak hours.
- Risk of blocking payments when the mTLS certificate between the API and payment gateway expires.
- Risk of incorrect retry webhook deduplication and double debiting.

## Security
- [x] Performed SAST/DAST for backend API.
- [ ] Not closed high finding SEC-4821: there is no rate-limit restriction on the payment confirmation endpoint.
- [ ] Repeated pentest after fixing webhook signature validation was not completed.
- [x] Secrets for production are stored in vault and do not end up in the repository.

## Ops Readiness
- [x] Added alerts for error rate and latency checkout.
- [ ] 1500 RPS load run with evening peak profile not completed.
- [ ] There is no confirmed rollback dry-run on staging for the last 7 days.
- [x] Incident channel communication for the release window has been prepared.

## Approvals
- Product approval: APPROVED (owner: pm@company, 2026-04-19).
- QA sign-off: APPROVED (owner: qa-lead@company, 2026-04-20).
- Security approval: PENDING (owner: appsec@company).
- SRE approval: PENDING (owner: sre-oncall@company).
- Release manager approval: WAITING final decision.

## Rollback Plan
- The application version is rolled back to `payments-v1.42.3` via blue/green switch in 8 minutes.
- Migrations are rolled back by the `20260420_payments_v2_down.sql` script.
- After rollback, manual control of the webhook queue and reconciliation job is enabled.

## Monitoring
- Key KPIs: success_rate, p95 checkout latency, auth_decline_rate.
- GO requires: success_rate >= 97.5%, p95 <= 900ms, auth_decline_rate <= 4.5%.
- On-call channel: `#payments-release-war-room`, bridge: `ops-bridge-17`.
