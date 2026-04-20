# ADR-0022: Artifact Writer MCP MVP и PostgreSQL Artifact Store

- Статус: Accepted
- Дата: 2026-04-20

## Контекст

После `Increment 16` MCP-контур уже включал Retrieval и Repository сервисы, но отсутствовал отдельный runtime boundary для записи generated artifacts.

Оставались пробелы:

- не было отдельного persistence-контура для артефактов;
- отсутствовал MCP-контракт для записи/чтения/листа артефактов;
- runbook не покрывал ручной smoke artifact writer сценариев.

## Решение

1. Добавить выделенный persistence-слой артефактов:
   - `PostgresArtifactStore` с fallback режимом;
   - SQL миграция `0006_artifact_store.sql` (`app.artifacts` + индекс по `artifact_type/updated_at`).
2. Ввести application-сервис артефактов:
   - `ArtifactApplicationService` (`write_artifact`, `get_artifact`, `list_artifacts`).
3. Добавить Artifact Writer MCP MVP:
   - app entrypoint `apps/mcp_artifact_writer/main.py`;
   - сервис `FastMcpArtifactWriterService`;
   - MCP tools: `write_artifact`, `get_artifact`, `list_artifacts`.
4. Зафиксировать typed MCP контракты:
   - `schemas/mcp/artifact_writer.py`.
5. Добавить операционные скрипты и smoke:
   - запуск runtime `run_artifact_writer_mcp.sh/.ps1`;
   - ручной smoke `smoke_artifact_writer_mcp.py` + обертки `smoke_artifact_writer_mcp.sh/.ps1`.

## Последствия

Плюсы:

- MCP-контур доведен до трех сервисов: Retrieval + Repository + Artifact Writer;
- generated artifacts получили выделенный PostgreSQL storage и явный read/write контракт;
- ручной runbook теперь покрывает smoke для artifact writer контура.

Минусы:

- `list_artifacts` в MVP использует `limit/offset`, а не cursor pagination;
- Artifact Writer MCP пока без auth/rate-limit/observability политик;
- MVP не включает полноценный authoring workflow/assembly, а только storage-boundary и MCP tools.
