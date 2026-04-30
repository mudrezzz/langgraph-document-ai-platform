# OSS License Rationale

Дата обновления: 2026-04-30

## Рекомендованная лицензия

`Apache License 2.0`.

## Почему Apache-2.0

1. Разрешительная лицензия, удобная для интеграции в enterprise-контуры.
2. Явный grant по патентам, что снижает юридическую неопределенность для пользователей framework.
3. Совместима с моделью "internal-first -> external contributors".
4. Хорошо подходит для mixed-stack инфраструктурных проектов с API/MCP/contracts.

## Рассмотренные альтернативы

- MIT:
  - проще текстом, но нет явного patent grant.
- BSD-3-Clause:
  - тоже permissive, но чаще менее привычна для enterprise AI/platform tooling, чем Apache-2.0.

## Вывод

Для текущего профиля проекта (`framework + integrations + OSS extension path`) Apache-2.0 дает лучший баланс открытости и юридической предсказуемости.
