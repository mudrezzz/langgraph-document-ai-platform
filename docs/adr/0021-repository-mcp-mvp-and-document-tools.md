# ADR-0021: Repository MCP MVP и базовые document tools

- Статус: Accepted
- Дата: 2026-04-20

## Контекст

После `Increment 15` в системе уже был Retrieval MCP MVP, но отсутствовал отдельный MCP-контур для работы с документами репозитория. Это создавало GAP к целевой архитектуре:

- MCP boundary покрывал только retrieval-сценарий;
- не было стандартного MCP-контракта для операций `upsert/get/list` документов;
- ручной smoke MCP-контуров не включал проверку document repository tools.

## Решение

1. Добавить application-сервис документов:
   - `DocumentApplicationService` (`upsert_document`, `get_document`, `list_documents`);
   - модель страницы `DocumentListPage` для list-операций.
2. Расширить `PostgresDocumentRepository`:
   - поддержка list-операции `list_documents(limit, offset)` в PostgreSQL и fallback режиме;
   - fallback storage хранит `created_at/updated_at` для стабильного порядка list.
3. Ввести Repository MCP MVP:
   - app entrypoint `apps/mcp_repository/main.py`;
   - сервис `FastMcpRepositoryService`;
   - MCP tools: `upsert_document`, `get_document`, `list_documents`.
4. Зафиксировать typed MCP контракты:
   - `schemas/mcp/repository.py` (input/output модели для 3 tool-ов).
5. Добавить операционные скрипты и smoke:
   - запуск MCP runtime: `run_repository_mcp.sh/.ps1`;
   - ручной smoke: `smoke_repository_mcp.py` + обертки `smoke_repository_mcp.sh/.ps1`.

## Последствия

Плюсы:

- MCP-контур расширен вторым рабочим сервисом (`Repository MCP`) поверх существующего Retrieval MCP;
- появился типизированный контракт document tools для интеграции внешних MCP-клиентов;
- ручной runbook и smoke покрывают базовые document repository операции.

Минусы:

- `list_documents` в MVP использует `limit/offset`, а не cursor pagination;
- Repository MCP пока без auth/rate-limit/observability политик;
- MCP-сценарии пока ограничены базовыми CRUD/read-model операциями (без artifact writer и orchestration между MCP-сервисами).
