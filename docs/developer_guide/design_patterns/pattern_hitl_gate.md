# Pattern: HITL Gate Pattern

Когда применять:

- решение нельзя полностью автоматизировать без reviewer sign-off;
- нужен повторяемый path `needs_changes -> rewrite -> approve`;
- нужно хранить timeline reviewer actions для аудита.

## Скелет

`authoring/start_async -> waiting_human -> hitl/submit -> resume -> completed`

## Runnable пример

```bash
bash backend/scripts/async_up.sh
.venv/bin/python agent_examples/run_example.py --pattern hitl_gate --hitl-decisions needs_changes,approve
```

## Extension points

1. Настроить max iterations и timeout через `APP_HITL_*`.
2. Добавить reviewer roles/RBAC policy для sensitive decisions.
3. Добавить свои observability checks в release gate.

## Анти-паттерны

1. Не проверять `expected_iteration`/idempotency при submit.
2. Продолжать pipeline при `reject` как при `approve`.
3. Не закрывать async resources после smoke/rehearsal.
