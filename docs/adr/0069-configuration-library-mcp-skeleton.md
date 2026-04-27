# ADR-0069: Configuration Library MCP Skeleton

- Статус: Accepted
- Дата: 2026-04-27

## Контекст

К началу Increment 30 у платформы уже есть MCP boundaries для retrieval, repository, artifact writer, template library и reviewer/HITL. Но в целевой архитектуре из ТЗ также нужен отдельный контур для reusable configuration artifacts: типовых retrieval policies, governance bundles, quality profiles и похожих operational configs.

Без такого boundary внешнему агенту или оператору приходится либо хранить конфигурации вне платформы, либо напрямую знать внутренние таблицы и payload shape. Это противоречит цели Increment 30: сделать production-like service boundary, а не набор внутренних adapter entrypoints.

## Решение

1. Добавить отдельный persisted домен `configuration_library` с versioned JSON configuration records.
2. Реализовать application boundary `ConfigurationLibraryApplicationService` поверх `PostgresConfigurationStore`.
3. Добавить FastMCP service `configuration-library-mcp` с typed schemas `schemas.mcp.configuration_library`.
4. В первом production-compatible slice поддержать tools:
   - `upsert_config`;
   - `get_config`;
   - `list_configs`;
   - `find_similar_configs`;
   - `compare_configs`.
5. Для `find_similar_configs` использовать deterministic similarity heuristic поверх existing persisted records, а не вводить отдельный vector/runtime stack. Это достаточно для skeleton-слоя и не создает новую параллельную архитектуру.
6. `compare_configs` строить как deterministic payload diff по flattened JSON paths, чтобы caller видел изменившиеся настройки без доступа к raw storage internals.

## Последствия

Плюсы:

- MCP surface закрывает еще один обязательный сервис из ТЗ и blueprint;
- reusable policy/config bundles теперь можно хранить, версионировать, читать, сравнивать и искать аналоги через единый typed boundary;
- skeleton не тянет за собой новую retrieval/vector архитектуру и использует те же PostgreSQL/fallback patterns, что другие persisted services.

Минусы:

- similarity search пока heuristic и deterministic, без semantic/vector поиска по configuration intent;
- lifecycle/governance статусы для config bundles пока не введены и могут понадобиться отдельным следующим slice;
- pagination `find_similar_configs` пока работает поверх ограниченного candidate pool, что приемлемо для skeleton, но не для очень больших библиотек без дальнейшей индексации.
